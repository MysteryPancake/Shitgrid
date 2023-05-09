import bpy, os, argparse

blender_db = os.environ.get("SHITGRID_BLEND_DB")
if not blender_db:
	raise Exception("Missing environment variable SHITGRID_BLEND_DB!")

# ==============================================================================
# Kitsu uses Blender names for linking. I want to avoid this.
# Blender names must be unique, so Blender often renames things without consent.
# Instead of names, I use custom data to create an imaginary link.
# This avoids naming issues, but puts more emphasis on hierarchy and content.
# ==============================================================================
def add_link(block, file):
	# Never override association data
	if hasattr(block, "sg_asset"):
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
		# Assuming clean.py ran first, our collection is empty
		our_collection = bpy.context.scene.collection

		# There's no way to import just Scene Collections, so import scenes instead
		with bpy.data.libraries.load(file.path, link=False) as (their_data, new_data):
			new_data.scenes = their_data.scenes

		# Copy their Scene Collection stuff into ours
		for scene in new_data.scenes:
			for obj in scene.collection.objects:
				our_collection.objects.link(obj)
			for col in scene.collection.children:
				our_collection.children.link(col)
			# Done copying, remove the imported scene
			bpy.data.scenes.remove(scene)

		# Link all objects and collections (just for safety, only the top layer is needed)
		for obj in bpy.data.objects:
			add_link(obj, file)
		for col in bpy.data.collections:
			add_link(col, file)

		# Clean up extra data and unused scenes
		blacklist = [
			bpy.data.materials, bpy.data.lights, bpy.data.brushes, bpy.data.lightprobes,
			bpy.data.cameras, bpy.data.armatures, bpy.data.actions, bpy.data.palettes,
			bpy.data.textures, bpy.data.images, bpy.data.speakers, bpy.data.linestyles
		]
		for junk in blacklist:
			for item in junk:
				junk.remove(item)
		kill_orphans()

class Layer_Materials:
# ========================================================================
# MATERIALS LAYER
# This assumes models exist in the scene, and transfers materials to them
# Brushes, palettes could be split into a separate surfacing library layer
# ========================================================================
	@staticmethod
	def process(file):
		our_collection = bpy.context.scene.collection

		with bpy.data.libraries.load(file.path, link=False) as (their_data, new_data):
			new_data.scenes = their_data.scenes
			new_data.images = their_data.images
			new_data.materials = their_data.materials
			new_data.brushes = their_data.brushes
			new_data.grease_pencils = their_data.grease_pencils
			new_data.paint_curves = their_data.paint_curves
			new_data.palettes = their_data.palettes
			new_data.textures = their_data.textures
			new_data.linestyles = their_data.linestyles

		# TODO: ASSIGN MATERIALS TO MODELS
		print("TODO")
		for scene in new_data.scenes:
			bpy.data.scenes.remove(scene)
		kill_orphans()

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
		#Layer_Materials.process(self.__get_latest("materials"))

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