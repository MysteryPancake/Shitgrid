import bpy, os, argparse

blender_db = os.environ.get("SHITGRID_BLEND_DB")
if not blender_db:
	raise OSError("Missing environment variable SHITGRID_BLEND_DB!")

# ==============================================================================
# Kitsu uses Blender names to represent links. I want to avoid this.
# Blender names must be unique, so Blender often renames things without consent.
# Instead of names, I used custom data to represent links.
# This avoids naming issues, but puts more emphasis on hierarchy.
# ==============================================================================
def add_link(block, asset, layer, version):
	# Only add, don't override
	if block.get("sg_asset"):
		return
	block["sg_asset"] = asset
	block["sg_layer"] = layer
	block["sg_version"] = version

class Source_File:
	def __init__(self, path, name, layer, version):
		self.path = path 		# String: Full path to layer Blend file
		self.name = name 		# String: Asset name
		self.layer = layer 		# String: Task layer
		self.version = version 	# UInt: Layer version (starts at 1)

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

# =========================================================
# Ideally children have a shared root collection:
# Human_Emily.blend:
# -> "Emily"
#    -> "Head"
#    -> "Body"
#    -> "Feet"
# However they could be loose:
# Human_Joe.blend:
# -> "Head"
# -> "Body"
# -> "Feet"
# Both cases are handled by find_roots:
# ["Emily"] for Emily, ["Head", "Body", "Feet"] for Joe
# =========================================================
class Transfer_Map:
	def __find_roots(self, parent, roots):
		for col in parent.children:
			if col.get("sg_asset") == self.file.name:
				roots.append((col, col.all_objects))
			else:
				self.__find_roots(col, roots)
		for obj in parent.objects:
			if obj.get("sg_asset") == self.file.name:
				roots.append((obj, obj.children_recursive))

	# If comparing names, strip .001 suffix
	def __clean_name(self, name):
		dot_index = name.rfind(".")
		if dot_index >= 0:
			return name[:dot_index]
		else:
			return name

	def __find_matches(self):
		our_roots = []
		their_roots = []
		self.__find_roots(bpy.context.scene.collection, our_roots)
		self.__find_roots(self.scene.collection, their_roots)

		# For now, only support exact matches
		if len(our_roots) != len(their_roots):
			raise Exception("NOT EXACT MATCH! (Root length)")

		matches = {}
		for root_us, root_them in zip(our_roots, their_roots):
			if len(root_us) != len(root_them):
				raise Exception("NOT EXACT MATCH! (Root child length)")

			for child_us, child_them in zip(root_us[1], root_them[1]):
				if child_us.type != child_them.type:
					raise Exception("NOT EXACT MATCH! (Child type)")
				#if self.__clean_name(child_us.name) != self.__clean_name(child_them.name):
					#raise Exception("NOT EXACT MATCH! (Child name)")

				matches[child_us] = child_them

		return matches

	def __init__(self, file):
		self.file = file

	def __enter__(self):
		self.scene = load_scene(self.file.path)
		return self.__find_matches()

	def __exit__(self, exc_type, exc_value, exc_traceback):
		unload_scene(self.scene)
		kill_orphans()

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

#class Layer_Lights:
	# ========================================================================
	# LIGHTS LAYER
	# Adds, updates or removes lights within the scene to match file
	# ========================================================================
	#@staticmethod
	#def process(file):
		# scene = load_scene(file.path)
		# TODO
		# unload_scene(scene)

class Asset_Builder:
	def __init__(self, asset):
		self.asset = asset

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
		path = versions[latest - 1]
		return Source_File(path, self.asset, layer, latest)

	def asset_library_build(self):
		# Load base geometry from modelling
		Layer_Base.process(self.__get_latest("models"))

		# Apply materials from surfacing
		Layer_Materials.process(self.__get_latest("materials"))

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

	def save(self):
		# Structure is "master/build/asset/asset_v001.blend" for now
		build_folder = os.path.join(blender_db, "build", self.asset)
		if not os.path.exists(build_folder):
			os.makedirs(build_folder)

		# Up version number based on file index in subfolder
		version = len([f for f in os.listdir(build_folder) if f.endswith(".blend")]) + 1

		# Name is "asset_v001.blend" for now
		file_name = "{}_v{:03d}.blend".format(self.asset, version)
		file_path = os.path.join(build_folder, file_name)

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
	builder.save()