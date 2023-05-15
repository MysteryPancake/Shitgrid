import bpy

# Utility struct for stuff relating to an asset layer
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
	with bpy.data.libraries.load(path, link=False) as (their_data, our_data):
		our_data.scenes = [their_data.scenes[0]]
	return our_data.scenes[0]

def unload_scene(scene: bpy.types.Scene) -> None:
	# Wipe fake users, ensure data gets orphaned
	for obj in scene.collection.all_objects:
		obj.use_fake_user = False
	for col in scene.collection.children_recursive:
		col.use_fake_user = False
	# Remove scene, this keeps the data block
	bpy.data.scenes.remove(scene)
	# Wipe scene data block and anything else left over
	bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)