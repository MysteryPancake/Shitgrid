import bpy, os, argparse, getpass
from uuid import uuid4
from difflib import SequenceMatcher as SM

blender_db = os.environ.get("SHITGRID_BLEND_DB")
if not blender_db:
	raise OSError("Missing environment variable SHITGRID_BLEND_DB!")

class Source_File:
	# Path: String - Full path to layer file
	# Name: String - Asset name
	# Layer: String - Layer name
	# Version: UInt - Layer version (starts at 1)
	def __init__(self, path, name, layer, version):
		self.path = path
		self.name = name
		self.layer = layer
		self.version = version

def load_scene(path):
	with bpy.data.libraries.load(path, link=False) as (their_data, our_data):
		our_data.scenes = [their_data.scenes[0]]
	return our_data.scenes[0]

def unload_scene(scene):
	# Wipe fake users, ensure data gets orphaned
	for obj in scene.collection.all_objects:
		obj.use_fake_user = False
	for col in scene.collection.children_recursive:
		col.use_fake_user = False
	bpy.data.scenes.remove(scene)

def kill_orphans():
	bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

# =====================================================================
# What the hell does this code do? Great question!

# The idea is a scene consists of data blocks tagged with custom data
# These exist in a tree hierarchy of parent-child relationships
# We need to respect the hierarchy when updating data
# To achieve this, try to find roots and reconstruct from there

# Roots are the topmost collections/objects belonging to a tag

# Assets may have a single root:
# Zoe.blend
# -> Zoe_Collection (ROOT, sg_asset="zoe")
#   -> Head_Object (sg_asset="zoe")
#   -> Body_Object (sg_asset="zoe")
#   -> Feet_Object (sg_asset="zoe")

# Or multiple roots:
# Tom.blend
# -> Head_Object (ROOT, sg_asset="tom")
# -> Body_Object (ROOT, sg_asset="tom")
# -> Feet_Object (ROOT, sg_asset="tom")

# Roots can exist inside eachother:
# Scene.Blend
# -> Shot_01 (ROOT, sg_asset="shot1")
#   -> Zoe_Collection (ROOT, sg_asset="zoe")
#   -> Head_Object (ROOT, sg_asset="tom")
#   -> Body_Object (ROOT, sg_asset="tom")
#   -> Feet_Object (ROOT, sg_asset="tom")

# I wanted to keep this flexible, so roots can be moved and renamed
# To find roots, Transfer_Map depth-first searches for matching tags
# Untagged children in our roots are considered part of us

# Next, Similarity_Data finds similar data blocks with matching tags
# This makes it flexible to structural and naming changes
# This is huge overkill for most situations, but why not :)
# =====================================================================
class Similarity_Data:
	def __init__(self, data, depth):
		self.name = self.__clean_name(data.name)
		self.data_count = self.__count_data(data)
		self.data = data
		self.depth = depth

	# When comparing names, strip .001 suffix
	def __clean_name(self, name):
		dot_index = name.rfind(".")
		if dot_index >= 0:
			return name[:dot_index]
		else:
			return name

	def __count_data(self, obj):
		# Only supported on objects for now
		if type(obj) != bpy.types.Object:
			return
		# TODO: Support more types
		if obj.type == "MESH":
			return [len(obj.data.vertices), len(obj.data.edges), len(obj.data.polygons)]
		elif obj.type == "CURVE":
			return [len(obj.data.splines)]

	# Compute difference exponentially, just for fun
	def __pow_diff(self, power, a, b):
		return pow(power, -abs(a - b))

	def compare(self, them):
		# Name similarity
		score = SM(None, self.name, them.name).quick_ratio()
		# Tree depth similarity
		score += self.__pow_diff(2.0, self.depth, them.depth) * 2
		# Data similarity
		if self.data_count and them.data_count:
			for a, b in zip(self.data_count, them.data_count):
				score += self.__pow_diff(1.1, a, b)
		return score

class Transfer_Map:
	def __traverse_trees(self, data, col, depth=0, in_root=False):
		for child in col.children:
			# Prevent loops influencing eachother
			depth_edit = depth
			in_root_edit = in_root

			child_name = child.get("sg_asset")
			# Assume untagged children in our roots are part of us
			if child_name:
				# Only change root state when we hit a different asset
				in_root_edit = child_name == self.file.name
			if in_root_edit:
				# Don't include collections for now
				# data["COLLECTION"].append(Similarity_Data(child, depth_edit))
				depth_edit += 1
			else:
				# Depth is relative to our roots
				depth_edit = 0
			# Depth-first search
			self.__traverse_trees(data, child, depth_edit, in_root_edit)

		# Same as above but for objects
		for obj in col.objects:
			in_root_edit = in_root
			obj_name = obj.get("sg_asset")
			if obj_name:
				in_root_edit = obj_name == self.file.name
			if in_root_edit:
				if not obj.type in data:
					data[obj.type] = []
				data[obj.type].append(Similarity_Data(obj, depth))

	def __find_matches(self):
		our_data = {}
		their_data = {}
		self.__traverse_trees(our_data, bpy.context.scene.collection)
		self.__traverse_trees(their_data, self.scene.collection)

		matches = {}
		for category in our_data:
			for us in our_data[category]:
				if not category in their_data:
					print("ERROR: Missing category " + category)
					continue
				
				# We love O(n^2) complexity
				best_score = 0
				best_item = None
				for them in their_data[category]:
					score = us.compare(them)
					if score > best_score:
						best_score = score
						best_item = them

				if best_score >= 1:
					print("Matched {} with {} ({} score)".format(us.data.name, best_item.data.name, best_score))
					matches[us.data] = best_item.data
				else:
					print("ERROR: Could not match {} ({} score)".format(us.data.name, best_score))

		return matches

	def __init__(self, file):
		self.file = file

	def __enter__(self):
		self.scene = load_scene(self.file.path)
		print("========================================================")
		print("Transferring {}...".format(self.file.path))
		print("========================================================")
		return self.__find_matches()

	def __exit__(self, exc_type, exc_value, exc_traceback):
		unload_scene(self.scene)
		kill_orphans()
		print("========================================================")
		print("Finished transferring {}".format(self.file.path))
		print("========================================================")

class Layer_Base:
	# ========================================================================
	# BASE LAYER
	# The deepest build layer, only used when headlessly building
	# Extracts stuff from modelling without materials, rigs, etc
	# ========================================================================
	@staticmethod
	def process(file):
		# No way to import just Scene Collections, so import scene instead
		scene = load_scene(file.path)

		# Copy top level stuff, children copy automatically
		for obj in scene.collection.objects:
			bpy.context.scene.collection.objects.link(obj)
		for col in scene.collection.children:
			bpy.context.scene.collection.children.link(col)

		# Done copying, remove the imported scene
		unload_scene(scene)

		# Wipe extra data
		blacklist = [
			"materials", "lights", "brushes", "lightprobes", "cameras", "armatures",
			"actions", "palettes", "textures", "images", "speakers", "linestyles"
		]
		for junk in blacklist:
			data_blocks = getattr(bpy.data, junk)
			for block in data_blocks:
				data_blocks.remove(block)

		kill_orphans()

class Layer_Materials:
	# ========================================================================
	# MATERIALS LAYER
	# Assuming models exist within the scene, transfers on materials
	# ========================================================================
	@staticmethod
	def process(file):
		with Transfer_Map(file) as lookup:
			for us, them in lookup.items():
				# Wipe our material slots
				while len(us.material_slots) > len(them.material_slots):
					us.active_material_index = len(them.material_slots)
					bpy.ops.object.material_slot_remove({"object": us})

				# Transfer material slots
				for idx in range(len(them.material_slots)):
					if idx >= len(us.material_slots):
						bpy.ops.object.material_slot_add({"object": us})
					us.material_slots[idx].link = them.material_slots[idx].link
					us.material_slots[idx].material = them.material_slots[idx].material

				# Transfer active material slot
				us.active_material_index = them.active_material_index

				if us.type == "CURVE":
					# Transfer curve material
					for spl_to, spl_from in zip(us.data.splines, them.data.splines):
						spl_to.material_index = spl_from.material_index

				elif us.type == "MESH":
					# Transfer face data
					for pol_to, pol_from in zip(us.data.polygons, them.data.polygons):
						pol_to.material_index = pol_from.material_index
						pol_to.use_smooth = pol_from.use_smooth

					# Transfer UV seams
					for edge_to, edge_from in zip(us.data.edges, them.data.edges):
						edge_to.use_seam = edge_from.use_seam

					# Wipe our UV layers
					while len(us.data.uv_layers) > 0:
						us.data.uv_layers.remove(us.data.uv_layers[0])

					# Transfer UV layers
					for uv_from in them.data.uv_layers:
						uv_to = us.data.uv_layers.new(name=uv_from.name, do_init=False)
						for loop in us.data.loops:
							uv_to.data[loop.index].uv = uv_from.data[loop.index].uv

					# Make sure correct UV layer is active
					for uv_l in them.data.uv_layers:
						if uv_l.active_render:
							us.data.uv_layers[uv_l.name].active_render = True
							break

					# Wipe our vertex colors
					while len(us.data.vertex_colors) > 0:
						us.data.vertex_colors.remove(us.data.vertex_colors[0])

					# Transfer vertex colors
					for vcol_from in them.data.vertex_colors:
						vcol_to = us.data.vertex_colors.new(name=vcol_from.name, do_init=False)
						for loop in us.data.loops:
							vcol_to.data[loop.index].color = vcol_from.data[loop.index].color

class Asset_Builder:
	def __init__(self, asset):
		self.asset = asset
		self.uuid = str(uuid4())

	def __get_versions(self, layer):
		# Structure is "master/wip/asset/layer/asset_layer_v001.blend" for now
		wip_folder = os.path.join(blender_db, "wip", self.asset, layer)
		if not os.path.exists(wip_folder):
			raise NotADirectoryError("Missing {} folder: {}".format(layer, wip_folder))
		# Sort by name to retrieve correct version order
		return sorted([os.path.join(wip_folder, f) for f in os.listdir(wip_folder) if f.endswith(".blend")])

	def __get_latest(self, layer):
		versions = self.__get_versions(layer)
		latest = len(versions)
		if latest <= 0:
			raise FileNotFoundError("Missing {} file!".format(layer))
		return Source_File(versions[latest - 1], self.asset, layer, latest)

	def __mark_asset(self):
		# Ensure a root collection for Asset Browser listing
		root = None
		base = bpy.context.scene.collection

		if len(base.objects) == 0 and len(base.children) == 1:
			# If there's already a root collection, don't add another
			root = base.children[0]
			root.name = self.asset
		else:
			root = bpy.data.collections.new(self.asset)
			# Move children to new root collection
			for col in base.children:
				root.children.link(col)
				base.children.unlink(col)
			for obj in base.objects:
				root.objects.link(obj)
				base.objects.unlink(obj)
			# Add root collection to scene
			base.children.link(root)

		root.asset_mark()
		root.asset_generate_preview()

		asset_data = root.asset_data
		asset_data.catalog_id = self.uuid
		asset_data.author = getpass.getuser()

	def asset_library_build(self):
		# Load base geometry from modelling
		Layer_Base.process(self.__get_latest("models"))

		# Apply materials from surfacing
		Layer_Materials.process(self.__get_latest("materials"))

		# Prepare for asset browser
		self.__mark_asset()

	def __update_catalog(self, version):
		# Update catalog manually
		catalog_path = os.path.join(blender_db, "build", "blender_assets.cats.txt")
		catalog_exists = os.path.isfile(catalog_path)
		with open(catalog_path, "a") as catalog:
			if not catalog_exists:
				# Write default content, requires a folder UUID for some reason
				catalog.write("VERSION 1\n\n{}:Builds:Builds".format(str(uuid4())))
			# Structure is "Builds/Asset/Asset v001" for now
			name = self.asset.capitalize()
			catalog.write("\n{}:Builds/{}:{} v{:03d}".format(self.uuid, name, name, version))

	def save(self, write_catalog=False):
		# Structure is "master/build/asset/asset_v001.blend" for now
		asset_folder = os.path.join(blender_db, "build", self.asset)
		if not os.path.exists(asset_folder):
			os.makedirs(asset_folder)

		# Up version number based on file index in subfolder
		version = len([f for f in os.listdir(asset_folder) if f.endswith(".blend")]) + 1

		# Name is "asset_v001.blend" for now
		file_name = "{}_v{:03d}.blend".format(self.asset, version)
		file_path = os.path.join(asset_folder, file_name)

		if write_catalog:
			self.__update_catalog(version)

		bpy.ops.wm.save_mainfile(filepath=file_path)
		print("Successfully built {}".format(file_path))

def get_args():
	parser = argparse.ArgumentParser()
	_, all_args = parser.parse_known_args()

	# Blender returns all arguments after the --, discard everything before it
	dash_index = all_args.index("--")
	script_args = all_args[dash_index + 1:]

	# Put custom arguments here
	parser.add_argument("-a", "--asset", help="Asset name to build")
	parsed_args, _ = parser.parse_known_args(script_args)
	return parsed_args

if __name__ == "__main__":
	args = get_args()
	builder = Asset_Builder(args.asset)
	#builder = Asset_Builder("debug")
	builder.asset_library_build()
	builder.save(write_catalog=True)