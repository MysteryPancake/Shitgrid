from typing import Any, Optional, Union
import bpy

from .utils import *

class TransferSettings:
	"""Settings used when applying build layers"""
	update_transform: bool = True

class TransferMap:
	"""
	Finds new, deleted and matching data blocks using IDs.\n
	If multiple blocks share the same ID, it matches by order.
	"""
	def __add_new(self, item: Any) -> None:
		"""Registers a new collection or object"""
		if type(item) == bpy.types.Collection:
			self.new_cols.append(item)
		else:
			self.new_objs.append(item)
	
	def __add_deleted(self, item: Any) -> None:
		"""Registers a deleted collection or object"""
		if type(item) == bpy.types.Collection:
			self.deleted_cols.append(item)
		else:
			self.deleted_objs.append(item)
	
	def __add_match(self, target: Any, source: Any) -> None:
		"""Registers a matching collection or object"""
		if type(source) == bpy.types.Collection:
			self.matching_cols[target] = source
		else:
			self.matching_objs[target] = source
			# For rare case in modelling layer
			self.matching_objs_target[source] = target

	def __find_ids(self, data_blocks: list[Any], ids: dict[str, list[Any]]) -> None:
		"""Builds a dict to easily check whether an ID exists"""

		for block in data_blocks:
			name = block.get("sg_asset")
			if not name:
				continue
			
			# Ignore blocks outside our namespace
			if name != self.file.name:
				continue

			id = block.get("sg_id")
			if not id:
				continue

			# Use a list in case multiple blocks share the same ID
			if id not in ids:
				ids[id] = []
			ids[id].append(block)

	def __find_matches(self):
		"""Finds added, removed and matching data blocks using IDs"""

		source_col = self.scene.collection
		target_col = bpy.context.scene.collection

		# Find IDs in the other scene
		self.__find_ids(source_col.all_objects, self.source_ids)
		self.__find_ids(source_col.children_recursive, self.source_ids)

		# Find IDs in the current scene
		self.__find_ids(target_col.all_objects, self.target_ids)
		self.__find_ids(target_col.children_recursive, self.target_ids)

		# Find matching and added IDs
		for source_id in self.source_ids:
			# List in case multiple objects share the same ID
			sources: list[Any] = self.source_ids[source_id]
			if source_id in self.target_ids:
				targets: list[Any] = self.target_ids[source_id]
				# When IDs are shared, match by index order
				for i in range(len(targets)):
					self.__add_match(targets[i], sources[min(i, len(sources) - 1)])
			else:
				for source in sources:
					self.__add_new(source)

		# Find deleted IDs
		for target_id in self.target_ids:
			# This code only handles cases where the ID is unique.
			# If the ID isn't unique, I don't know how to handle it.
			# In that case, source_ids[id] and target_ids[id] have different lengths.
			# What to remove? The start of the list? The end of the list?
			# If the order doesn't match, it'll remove stuff at random.
			# I think it's better to remove nothing.
			if target_id not in self.source_ids:
				for target in self.target_ids[target_id]:
					self.__add_deleted(target)
	
	def __find_parents(self, col: bpy.types.Collection) -> None:
		"""Finds parents of all child objects and collections in the other scene"""
		for child in col.children:
			if col != self.scene.collection:
				self.parents[child] = col
			self.__find_parents(child)

		for obj in col.objects:
			if col != self.scene.collection:
				self.parents[obj] = col
	
	def __attempt_match(self, col: bpy.types.Collection) -> Optional[bpy.types.Collection]:
		"""Tries to find a matching parent collection"""
		col_id = col.get("sg_id")
		if col_id and col_id in self.target_ids:
			return self.target_ids[col_id][0]

	def __self_reference_collection(self, col: bpy.types.Collection) -> None:
		"""When linking a collection from the other scene, fixes missing ID data"""

		self.matching_cols[col] = col
		col_id = col.get("sg_id")
		if not col_id:
			return
		
		if col_id not in self.target_ids:
			self.target_ids[col_id] = []
			
		self.target_ids[col_id].append(col)
	
	def remove_blank_collections(self) -> None:
		"""Removes collections deleted from a layer if blank"""
		for col in self.deleted_cols:
			# For safety, only remove blank collections
			if not col.children and not col.objects:
				bpy.data.collections.remove(col)

	def rebuild_collection_parents(self, obj: bpy.types.Object) -> bpy.types.Collection:
		"""Reconstructs the collection hierarchy of an object"""
		# Top-level objects don't need special treatment
		if obj not in self.parents:
			return bpy.context.collection

		parent = self.parents[obj]
		# If we have this collection already, reuse it
		matching = self.__attempt_match(parent)
		if matching:
			return matching
		
		# We don't, wipe and use the other one
		wipe_collection(parent)
		self.__self_reference_collection(parent)

		# Reconstruct missing collections
		top = parent
		while top in self.parents:
			# Move up a level
			bottom = top
			top = self.parents[top]

			# If we have this collection already, reuse it
			matching = self.__attempt_match(top)
			if matching:
				matching.children.link(bottom)
				return parent
			
			# We don't, wipe and use the other one
			wipe_collection(top)
			self.__self_reference_collection(top)
			top.children.link(bottom)

		# Started at the bottom now we're here
		bpy.context.collection.children.link(top)
		return parent

	def __init__(self, file: SourceFile, find_parents: bool=True):
		self.file = file
		self.scene = load_scene(file.path)

		# For rare case in modelling layer
		self.matching_objs_target: dict[bpy.types.Object, bpy.types.Object] = {}

		self.matching_objs: dict[bpy.types.Object, bpy.types.Object] = {}
		self.matching_cols: dict[bpy.types.Collection, bpy.types.Collection] = {}
		self.new_objs: list[bpy.types.Object] = []
		self.new_cols: list[bpy.types.Collection] = []
		self.deleted_objs: list[bpy.types.Object] = []
		self.deleted_cols: list[bpy.types.Collection] = []

		self.source_ids: dict[str, list[Any]] = {}
		self.target_ids: dict[str, list[Any]] = {}
		self.__find_matches()

		if find_parents:
			self.parents: dict[
				Union[bpy.types.Object, bpy.types.Collection],
				Union[bpy.types.Object, bpy.types.Collection]
			] = {}
			self.__find_parents(self.scene.collection)
		
	def close(self):
		"""In case you don't want to use `with`"""
		unload_scene(self.scene)

	def __enter__(self):
		"""Used with `with TransferMap(...) as map:`"""
		return self

	def __exit__(self, exc_type, exc_value, exc_traceback):
		self.close()