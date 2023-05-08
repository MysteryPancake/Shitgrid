import bpy, os, argparse
from layers import *

blender_db = os.environ.get("SHITGRID_BLEND_DB")
if not blender_db:
	raise Exception("Missing environment variable SHITGRID_BLEND_DB!")

# The builder is responsible for constructing asset versions
class Asset_Builder:
	def __init__(self, asset):
		self.asset = asset

	def __find_version(self, layer, version=-1):
		# Structure is "master/wip/asset/layer/asset_layer_v001.blend" for now
		wip_folder = os.path.join(blender_db, "wip", self.asset, layer)
		if not os.path.exists(wip_folder):
			raise NotADirectoryError("Missing {} folder: {}".format(layer, wip_folder))

		# Sort by name to retrieve correct version order
		files = sorted([p for p in os.listdir(wip_folder) if p.endswith(".blend")])

		# This throws an IndexError if the version doesn't exist
		return os.path.join(wip_folder, files[version])

	def build_full(self):
		# Start with core layer, based on model data
		blend = self.__find_version("models", -1)
		Layer_Core.process(blend)

	def save(self):
		# Structure is "master/build/asset/asset_v001.blend" for now
		build_folder = os.path.join(blender_db, "build", self.asset)
		if not os.path.exists(build_folder):
			os.makedirs(build_folder)

		# Up version number based on file index in subfolder
		version = len([p for p in os.listdir(build_folder) if p.endswith(".blend")]) + 1

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
	builder.build_full()
	builder.save()