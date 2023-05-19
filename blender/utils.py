from typing import Any
import bpy

class SourceFile:
	"""
	Struct representing a Blender asset layer file.\n
	Path: Full path to layer file, eg. `"path\\to\\cube_model_v001.blend"`
	Name: Asset name, eg. `"cube"`
	Layer: Layer name, eg. `"models"`
	Version: Layer version, starting at 1.
	"""
	def __init__(self, path: str, name: str, layer: str, version: int):
		self.path = path
		self.name = name
		self.layer = layer
		self.version = version

def load_scene(path: str) -> bpy.types.Scene:
	"""Loads the first scene of the file into our scene"""
	with bpy.data.libraries.load(path, link=False) as (source_data, target_data):
		target_data.scenes = [source_data.scenes[0]]
	return target_data.scenes[0]

def unload_scene(scene: bpy.types.Scene) -> None:
	"""Removes the scene and clears fake users and orphans"""
	for obj in scene.collection.all_objects:
		obj.use_fake_user = False
	for col in scene.collection.children_recursive:
		col.use_fake_user = False
	# This keeps the scene data block
	bpy.data.scenes.remove(scene)
	# Wipe the data block and kill the orphans (real)
	bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

def transfer_version(source: Any, target: Any) -> None:
	"""Transfers the version number between data blocks, useful when updating data"""
	source_version = source.get("sg_version")
	target_version = target.get("sg_version")
	# 0 is false, so check for None instead
	if source_version != None and target_version != None:
		target["sg_version"] = source["sg_version"]