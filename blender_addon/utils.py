import bpy

# Struct representing a Blender asset layer file
class SourceFile:
	# Path: Full path to layer file (path\to\cube_model_v001.blend)
	# Name: Asset name (cube)
	# Layer: Layer name (model)
	# Version: Layer version (starts at 1)
	def __init__(self, path: str, name: str, layer: str, version: int):
		self.path = path
		self.name = name
		self.layer = layer
		self.version = version

def load_scene(path: str) -> bpy.types.Scene:
	# Load the first scene in the file into our scene
	with bpy.data.libraries.load(path, link=False) as (source_data, target_data):
		target_data.scenes = [source_data.scenes[0]]
	return target_data.scenes[0]

def unload_scene(scene: bpy.types.Scene) -> None:
	# Clear fake users, ensure all data gets orphaned
	for obj in scene.collection.all_objects:
		obj.use_fake_user = False
	for col in scene.collection.children_recursive:
		col.use_fake_user = False
	# Remove scene, note this keeps the data block
	bpy.data.scenes.remove(scene)
	# Wipe scene data block and anything else left over
	bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)