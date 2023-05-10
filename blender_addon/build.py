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
def add_link(block, file):
	# Only add, don't override
	if block.get("sg_asset"):
		return
	block["sg_asset"] = file.name
	block["sg_layer"] = file.layer
	block["sg_version"] = file.version

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

# =========================================================
# Ideally assets sit within a master collection:
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
# To allow both cases, find roots
# ["Emily"] for Emily, ["Head", "Body", "Feet"] for Joe
# To achieve this, find_roots performs a depth-first search
# =========================================================
class Transfer_Map:
	def __find_roots(self, asset, parent, roots):
		for col in parent.children:
			if col.get("sg_asset") == asset:
				roots.append((col, col.all_objects))
			else:
				self.__find_roots(asset, col, roots)
		for obj in parent.objects:
			if obj.get("sg_asset") == asset:
				roots.append((obj, obj.children_recursive))

	# If comparing names, remove .001 suffix
	def __clean_name(self, name):
		dot_index = name.rfind(".")
		if dot_index >= 0:
			return name[:dot_index]
		else:
			return name

	def __find_matches(self, asset, us, them):
		our_roots = []
		their_roots = []
		self.__find_roots(asset, us, our_roots)
		self.__find_roots(asset, them, their_roots)
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
				if self.__clean_name(child_us.name) != self.__clean_name(child_them.name):
					raise Exception("NOT EXACT MATCH! (Child name)")
				matches[child_us] = child_them
		return matches

	def __init__(self, file):
		self.file = file

	def __enter__(self):
		self.scene = load_scene(self.file.path)
		our_collection = bpy.context.scene.collection
		return self.__find_matches(self.file.name, our_collection, self.scene.collection)

	def __exit__(self, exc_type, exc_value, exc_traceback):
		bpy.data.scenes.remove(self.scene)

def kill_orphans():
	bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

class Layer_Base:
	# ========================================================================
	# BASE LAYER
	# The deepest build layer, only used when headlessly building
	# Extracts stuff from modelling without materials, rigs, etc
	# ========================================================================
	@staticmethod
	def process(file):
		# Add a root collection for Asset Browser listing
		root = bpy.data.collections.new(file.name)
		root.asset_mark()
		bpy.context.scene.collection.children.link(root)

		# No way to import just Scene Collections, so import scene instead
		scene = load_scene(file.path)

		# If artist made a parent collection, don't add another layer
		parent = scene.collection
		if len(parent.objects) == 0 and len(parent.children) == 1:
			parent = parent.children[0]

		# Copy top level, children copy automatically
		for obj in parent.objects:
			root.objects.link(obj)
		for col in parent.children:
			root.children.link(col)

		# Done copying, remove the imported scene
		bpy.data.scenes.remove(scene)

		# Link added data blocks
		add_link(root, file)
		for col in root.children_recursive:
			add_link(col, file)
		for obj in root.all_objects:
			add_link(obj, file)

		# Clean up extra data and unused scenes
		blacklist = [
			"materials", "lights", "brushes", "lightprobes", "cameras", "armatures",
			"actions", "palettes", "textures", "images", "speakers", "linestyles"
		]
		for junk in blacklist:
			data = getattr(bpy.data, junk)
			for block in data:
				data.remove(block)

		kill_orphans()

class Layer_Materials:
	# ========================================================================
	# MATERIALS LAYER
	# This assumes models exist in the scene, and transfers materials to them
	# ========================================================================
	@staticmethod
	def process(lookup):
		for us, them in lookup.items():

			# Wipe our material slots, same as Kitsu
			bpy.ops.object.material_slot_remove_unused({"object": us})
			while len(us.material_slots) > len(them.material_slots):
				us.active_material_index = len(them.material_slots)
				bpy.ops.object.material_slot_remove({"object": us})

			# Transfer their material slots
			for idx in range(len(them.material_slots)):
				if idx >= len(us.material_slots):
					bpy.ops.object.material_slot_add({"object": us})
				us.material_slots[idx].link = them.material_slots[idx].link
				us.material_slots[idx].material = them.material_slots[idx].material

			# Transfer their active material slot
			us.active_material_index = them.active_material_index

			#print(us.name + " = " + them.name)
		#add_links(__class__.links, file)

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

	def build_full(self):
		# Load base geometry from modelling
		Layer_Base.process(self.__get_latest("models"))

		# Load materials from surfacing
		with Transfer_Map(self.__get_latest("materials")) as transfers:
			Layer_Materials.process(transfers)
		kill_orphans()

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
	#args = get_args()
	#builder = Asset_Builder(args.asset)
	builder = Asset_Builder("debug")
	builder.build_full()
	#builder.save()