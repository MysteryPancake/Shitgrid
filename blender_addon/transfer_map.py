from typing import Any
import bpy

from .utils import *

# UPDATE: I added UUIDs, making the explanation below outdated.
# I'll keep the old code commented here for now.

# =====================================================================
# What the hell does this code do? Great question!

# Kitsu uses Blender names to figure out asset links. I wanted to avoid this.
# Blender names must be unique, so Blender often renames things without consent.
# Instead of names, I currently use custom data to represent links.
# This avoids naming issues, but puts more emphasis on hierarchy.

# A scene consists of data blocks tagged with custom data.
# These exist in a tree hierarchy of parent-child relationships.
# We need to respect the hierarchy when updating data blocks.
# To achieve this, try to find roots and reconstruct from there.

# Roots are the topmost collections/objects belonging to a tag.

# Assets may have a single root:
# Zoe.blend
# -> Zoe_Collection (ROOT, sg_asset="zoe")
#   -> Head_Object (sg_asset="zoe")
#   -> Body_Object (sg_asset="zoe")
#   -> Feet_Object (sg_asset="zoe")

# Or multiple roots:
# Tom.blend
# -> Head_Object (ROOT, sg_asset="tom")
# -> Body_Object (ROOT, sg_asset="tom")
# -> Feet_Object (ROOT, sg_asset="tom")

# Roots can exist inside eachother:
# Scene.Blend
# -> Shot_01 (ROOT, sg_asset="shot1")
#   -> Zoe_Collection (ROOT, sg_asset="zoe")
#   -> Head_Object (ROOT, sg_asset="tom")
#   -> Body_Object (ROOT, sg_asset="tom")
#   -> Feet_Object (ROOT, sg_asset="tom")

# I wanted to keep this flexible, so roots can be moved and renamed.
# To find roots, TransferMap depth-first searches for matching tags.
# Untagged children in our roots are considered part of us.
# Next, Similarity finds similar data blocks.
# =====================================================================

class TransferMap:
	# Unmatching or unlabelled items are assumed new
	def __add_new(self, item: Any) -> None:
		if type(item) == bpy.types.Collection:
			self.new_cols.append(item)
		else:
			self.new_objs.append(item)
	
	# Matching items are stored for quick ID lookup
	def __add_match(self, target: Any, source: Any) -> None:
		if type(source) == bpy.types.Collection:
			self.matching_cols[target] = source
		else:
			self.matching_objs[target] = source

	def __find_ids(self, data_blocks: list[Any], ids: dict[str, list[Any]]) -> None:
		for block in data_blocks:
			name = block.get("sg_asset")
			# Untagged blocks may be new
			if not name:
				self.__add_new(block)
				continue

			# Ignore blocks outside our namespace
			if name != self.file.name:
				continue

			id = block.get("sg_id")
			if not id:
				self.__add_new(block)
				continue
			
			# ID lists are used in case multiple blocks share the same ID
			# This is invalid and should be handled when publishing
			if id not in ids:
				ids[id] = []
			ids[id].append(block)

	def __find_matches(self):
		source_col = self.scene.collection
		target_col = bpy.context.scene.collection

		source_ids = {}
		self.__find_ids(source_col.all_objects, source_ids)
		self.__find_ids(source_col.children_recursive, source_ids)

		target_ids = {}
		self.__find_ids(target_col.all_objects, target_ids)
		self.__find_ids(target_col.children_recursive, target_ids)

		# ID lists are used in case multiple blocks share the same ID
		for source_id in source_ids:
			sources: list[Any] = source_ids[source_id]
			if source_id in target_ids:
				targets: list[Any] = target_ids[source_id]
				for i in range(len(targets)):
					self.__add_match(targets[i], sources[min(i, len(sources) - 1)])
			else:
				for source in sources:
					self.__add_new(source)

	def __init__(self, file: SourceFile):
		self.file = file
		self.scene = load_scene(file.path)
		
		self.matching_objs = {}
		self.matching_cols = {}
		self.new_objs = []
		self.new_cols = []

		print(f"Transferring {file.path}...")
		self.__find_matches()
		
	def close(self):
		unload_scene(self.scene)
		print(f"Finished transferring {self.file.path}")

	# Used when calling "with TransferMap(...) as map:"
	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, exc_traceback):
		self.close()

"""
class _Similarity:
	# Fuzzy object matching. Currently obsolete due to UUIDs, but might come in handy later
	def __init__(self, data: Union[bpy.types.Collection, bpy.types.Object], depth: int, breadth: int):
		self.name = self.__clean_name(data.name)
		self.data_count = self.__count_data(data)
		self.data = data
		self.depth = depth
		self.breadth = breadth

	# When comparing names, strip any .001 suffixes
	def __clean_name(self, name: str) -> str:
		dot_index = name.rfind(".")
		if dot_index >= 0:
			return name[:dot_index]
		else:
			return name

	def __count_data(self, obj: Union[bpy.types.Collection, bpy.types.Object]):
		# Only supported on objects for now
		if type(obj) != bpy.types.Object:
			return
		if obj.type == "MESH":
			return [len(obj.data.vertices), len(obj.data.edges), len(obj.data.polygons)]
		elif obj.type == "CURVE":
			return [len(obj.data.splines)]

	# Compute difference exponentially, just for fun
	def __pow_diff(self, power: float, a: float, b: float) -> float:
		return pow(power, -abs(a - b))

	def compare(self, other) -> float:
		# Name similarity
		score = SequenceMatcher(None, self.name, other.name).quick_ratio()
		# Tree depth similarity (Y axis)
		score += self.__pow_diff(2.0, self.depth, other.depth) * 2.0
		# Tree breadth similarity (X axis)
		score += self.__pow_diff(2.0, self.breadth, other.breadth) * 2.0
		# Data similarity
		if self.data_count and other.data_count:
			for a, b in zip(self.data_count, other.data_count):
				score += self.__pow_diff(1.1, a, b)
		return score

class TransferMap_Old:
	# Similarity variant of tree traversal
	def __traverse_trees(
		self,
		data: dict[str, list[_Similarity]],
		col: bpy.types.Collection,
		depth: int=0,
		in_root=False
	) -> None:
		breadth = 0
		for child in col.children:
			# Prevent loops influencing eachother
			depth_edit = depth
			in_root_edit = in_root

			child_name = child.get("sg_asset")
			# Assume untagged children in our roots are part of us
			if child_name:
				# Only change root state when we hit a different asset
				in_root_edit = child_name == self.file.name
			if in_root_edit:
				# Don't include collections for now
				# data["COLLECTION"].append(Similarity(child, depth_edit, breadth))
				depth_edit += 1
				breadth += 1
			else:
				# Depth is relative to our roots
				depth_edit = 0
			# Depth-first search
			self.__traverse_trees(data, child, depth_edit, in_root_edit)

		# Same as above but for objects
		for obj in col.objects:
			in_root_edit = in_root
			obj_name = obj.get("sg_asset")
			if obj_name:
				in_root_edit = obj_name == self.file.name
			if in_root_edit:
				breadth += 1
				if obj.type not in data:
					data[obj.type] = []
				data[obj.type].append(_Similarity(obj, depth, breadth))

	def __find_matches(self):
		source_data = {}
		target_data = {}
		self.__traverse_trees(source_data, self.scene.collection)
		self.__traverse_trees(target_data, bpy.context.scene.collection)

		matches = {}
		for category in target_data:
			for target in target_data[category]:
				if category not in source_data:
					print(f"ERROR: Missing category '{category}'")
					continue
				
				# We love O(n^2) complexity
				best_score = 0
				source_item: Optional[_Similarity] = None
				for source in source_data[category]:
					score = target.compare(source)
					if score > best_score:
						best_score = score
						source_item = source

				if source_item and best_score >= 1:
					print(f"Matched '{target.data.name}' with '{source_item.data.name}' ({best_score} score)")
					matches[target.data] = source_item.data
				else:
					print(f"ERROR: Could not match '{target.data.name}' ({best_score} score)")

		return matches

	def __init__(self, file: SourceFile):
		self.file = file
		self.scene = load_scene(file.path)
		print("========================================================")
		print(f"Transferring {file.path}...")
		
	# Used when calling "with TransferMap(...) as map:"
	def __enter__(self):
		return self.__find_matches()

	def __exit__(self, exc_type, exc_value, exc_traceback):
		unload_scene(self.scene)
		print(f"Finished transferring {self.file.path}")
		print("========================================================")
"""