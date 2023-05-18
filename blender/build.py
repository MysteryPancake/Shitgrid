import bpy, os, argparse, getpass
from uuid import uuid4

from .layers import *
from .utils import *

class AssetBuilder:
	"""Constructs an asset by applying layers to the current scene."""
	def __init__(self, name: str):
		self.blender_db = os.environ.get("SG_BLEND_DB")
		if not self.blender_db:
			raise OSError("Missing environment variable SG_BLEND_DB!")
		
		self.asset = name
		self.uuid = str(uuid4())

	def __get_versions(self, layer: str):
		"""Returns a list of all files for a layer"""

		# Structure is "master/wip/asset/layer/asset_layer_v001.blend" for now
		wip_folder = os.path.join(self.blender_db, "wip", self.asset, layer)
		if not os.path.exists(wip_folder):
			raise NotADirectoryError(f"Missing {layer} folder: {wip_folder}")
		
		# Sort by name to retrieve correct version order
		versions = [os.path.join(wip_folder, f) for f in os.listdir(wip_folder) if f.endswith(".blend")]
		return sorted(versions)

	def __get_version(self, layer: str, version: int) -> SourceFile:
		"""Returns a layer file with a specific version"""

		versions = self.__get_versions(layer)
		if not versions:
			raise FileNotFoundError(f"No versions for {layer} exist!")
		
		num_versions = len(versions)
		if version <= 0 or version > num_versions:
			raise IndexError(f"Version {version} is out of range! Max is {num_versions}")
		
		# SourceFile expects a version number starting at 1
		return SourceFile(versions[version - 1], self.asset, layer, version)

	def __get_latest(self, layer: str) -> SourceFile:
		"""Returns the latest layer file available"""

		versions = self.__get_versions(layer)
		if not versions:
			raise FileNotFoundError(f"No versions for {layer} exist!")
		
		# SourceFile expects a version number starting at 1
		return SourceFile(versions[-1], self.asset, layer, len(versions))

	def mark_asset(self) -> None:
		"""Adds asset metadata and creates a root collection if needed"""

		root = None
		base = bpy.context.scene.collection
		if len(base.objects) == 0 and len(base.children) == 1:
			# If there's already a root collection, don't add another
			root = base.children[0]
			root.name = self.asset
		else:
			root = bpy.data.collections.new(self.asset)
			# Move children to new root collection
			move_children(base, root)
			# Add root collection to scene
			base.children.link(root)

		root.asset_mark()
		root.asset_generate_preview()

		asset_data = root.asset_data
		asset_data.catalog_id = self.uuid
		asset_data.author = getpass.getuser()

	def process(self, layer, version: int=-1) -> None:
		"""
		Applies a layer with a specific version.\n
		Zero or negative uses the latest version.
		"""
		path = self.__get_version(layer.folder, version) if version > 0 else self.__get_latest(layer.folder)
		layer.process(path)

	def __update_catalog(self, version: int) -> None:
		"""Manually updates Blender's Asset Library catalog file"""

		catalog_path = os.path.join(self.blender_db, "build", "blender_assets.cats.txt")
		catalog_exists = os.path.isfile(catalog_path)

		with open(catalog_path, "a") as catalog:
			if not catalog_exists:
				# Write default content, requires folders have UUIDs for some reason
				catalog.write(f"VERSION 1\n\n{uuid4()}:Builds:Builds")
			# Structure is "Builds/Asset/Asset v001" for now
			name = self.asset.capitalize()
			catalog.write(f"\n{self.uuid}:Builds/{name}:{name} v{version:03d}")

	def save(self, write_catalog: bool=False) -> None:
		"""
		Saves the current Blender file in the builds folder.\n
		`write_catalog` optionally lists this file in the Asset Library.
		"""
		# Structure is "master/build/asset/asset_v001.blend" for now
		asset_folder = os.path.join(self.blender_db, "build", self.asset)
		if not os.path.exists(asset_folder):
			os.makedirs(asset_folder)

		# Increase version based on file count in subfolder
		version = len([f for f in os.listdir(asset_folder) if f.endswith(".blend")]) + 1

		# Name is "asset_v001.blend" for now
		file_name = f"{self.asset}_v{version:03d}.blend"
		file_path = os.path.join(asset_folder, file_name)

		if write_catalog:
			self.__update_catalog(version)

		bpy.ops.wm.save_mainfile(filepath=file_path)
		print(f"Successfully built {file_path}")

def get_args():
	"""Gets arguments from the terminal (see `build.bat`)"""
	parser = argparse.ArgumentParser()
	_, all_args = parser.parse_known_args()

	# Blender returns all arguments after --, so discard everything before it
	dash_index = all_args.index("--")
	script_args = all_args[dash_index + 1:]

	# Put custom arguments here
	parser.add_argument("-a", "--asset", help="Asset name to build")
	parsed_args, _ = parser.parse_known_args(script_args)
	return parsed_args

if __name__ == "__main__":
	args = get_args()

	builder = AssetBuilder(args.asset)
	builder.process(LayerModelling)
	builder.process(LayerMaterials)
	builder.process(LayerRigging)
	builder.process(LayerGrooming)
	
	# When all layers are finished, this would be nice:
	# for layer in listed_layers:
		# builder.process(layer)

	builder.mark_asset()
	builder.save(write_catalog=True)