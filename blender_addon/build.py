import bpy, os, argparse, getpass
from uuid import uuid4

from .layers import *
from .utils import *

class AssetBuilder:
	def __init__(self, name: str):
		self.blender_db = os.environ.get("SG_BLEND_DB")
		if not self.blender_db:
			raise OSError("Missing environment variable SG_BLEND_DB!")
		self.asset = name
		self.uuid = str(uuid4())

	def __get_versions(self, layer: str):
		# Structure is "master/wip/asset/layer/asset_layer_v001.blend" for now
		wip_folder = os.path.join(self.blender_db, "wip", self.asset, layer)
		if not os.path.exists(wip_folder):
			raise NotADirectoryError("Missing {} folder: {}".format(layer, wip_folder))
		# Sort by name to retrieve correct version order
		versions = [os.path.join(wip_folder, f) for f in os.listdir(wip_folder) if f.endswith(".blend")]
		if not versions:
			raise FileNotFoundError("No versions for {} exist!".format(layer))
		return sorted(versions)

	def __get_version(self, layer: str, version: int):
		versions = self.__get_versions(layer)
		# SourceFile expects a version number starting at 1
		return SourceFile(versions[version - 1], self.asset, layer, version)

	def __get_latest(self, layer: str):
		versions = self.__get_versions(layer)
		# SourceFile expects a version number starting at 1
		return SourceFile(versions[-1], self.asset, layer, len(versions))

	def mark_asset(self):
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

	def process(self, layer):
		if not hasattr(layer, "folder"):
			raise NotImplementedError("{} has no associated folder!".format(layer))
		layer.process(self.__get_latest(layer.folder))

	def __update_catalog(self, version: int):
		# Update catalog manually
		catalog_path = os.path.join(self.blender_db, "build", "blender_assets.cats.txt")
		catalog_exists = os.path.isfile(catalog_path)
		with open(catalog_path, "a") as catalog:
			if not catalog_exists:
				# Write default content, requires a folder UUID for some reason
				catalog.write("VERSION 1\n\n{}:Builds:Builds".format(str(uuid4())))
			# Structure is "Builds/Asset/Asset v001" for now
			name = self.asset.capitalize()
			catalog.write("\n{}:Builds/{}:{} v{:03d}".format(self.uuid, name, name, version))

	def save(self, write_catalog: bool=False):
		# Structure is "master/build/asset/asset_v001.blend" for now
		asset_folder = os.path.join(self.blender_db, "build", self.asset)
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
	builder = AssetBuilder(args.asset)
	builder.process(LayerBase)
	builder.process(LayerMaterials)
	builder.mark_asset()
	builder.save(write_catalog=True)