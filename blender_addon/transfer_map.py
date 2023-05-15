import bpy
from difflib import SequenceMatcher as SM

from .utils import *

# =====================================================================
# What the hell does this code do? Great question!

# Kitsu uses Blender names to figure out asset links. I wanted to avoid this.
# Blender names must be unique, so Blender often renames things without consent.
# Instead of names, I currently use custom data to represent links.
# This avoids naming issues, but puts more emphasis on hierarchy.

# A scene consists of data blocks tagged with custom data.
# These exist in a tree hierarchy of parent-child relationships.
# We need to respect this hierarchy when updating data.
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

# Next, Similarity finds similar data blocks with matching tags.
# This makes it flexible to structural and naming changes.
# This is huge overkill for most situations, but why not :)
# =====================================================================

class Similarity:
	def __init__(self, data, depth: int):
		self.name = self.__clean_name(data.name)
		self.data_count = self.__count_data(data)
		self.data = data
		self.depth = depth

	# When comparing names, strip any .001 suffixes
	def __clean_name(self, name: str) -> str:
		dot_index = name.rfind(".")
		if dot_index >= 0:
			return name[:dot_index]
		else:
			return name

	def __count_data(self, obj):
		# Only supported on objects for now
		if type(obj) != bpy.types.Object:
			return
		# TODO: Support more types
		if obj.type == "MESH":
			return [len(obj.data.vertices), len(obj.data.edges), len(obj.data.polygons)]
		elif obj.type == "CURVE":
			return [len(obj.data.splines)]

	# Compute difference exponentially, just for fun
	def __pow_diff(self, power: float, a: float, b: float) -> float:
		return pow(power, -abs(a - b))

	def compare(self, them) -> float:
		# Name similarity
		score = SM(None, self.name, them.name).quick_ratio()
		# Tree depth similarity
		score += self.__pow_diff(2, self.depth, them.depth) * 2
		# Data similarity
		if self.data_count and them.data_count:
			for a, b in zip(self.data_count, them.data_count):
				score += self.__pow_diff(1.1, a, b)
		return score

class TransferMap:
	def __traverse_trees(self, data, col: bpy.types.Collection, depth: int=0, in_root=False) -> None:
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
				# data["COLLECTION"].append(Similarity(child, depth_edit))
				depth_edit += 1
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
				if not obj.type in data:
					data[obj.type] = []
				data[obj.type].append(Similarity(obj, depth))

	def __find_matches(self):
		our_data = {}
		their_data = {}
		self.__traverse_trees(our_data, bpy.context.scene.collection)
		self.__traverse_trees(their_data, self.scene.collection)

		matches = {}
		for category in our_data:
			for us in our_data[category]:
				if not category in their_data:
					print("ERROR: Missing category " + category)
					continue
				
				# We love O(n^2) complexity
				best_score = 0
				best_item = None
				for them in their_data[category]:
					score = us.compare(them)
					if score > best_score:
						best_score = score
						best_item = them

				if best_score >= 1:
					print("Matched {} with {} ({} score)".format(us.data.name, best_item.data.name, best_score))
					matches[us.data] = best_item.data
				else:
					print("ERROR: Could not match {} ({} score)".format(us.data.name, best_score))

		return matches

	def __init__(self, file: SourceFile):
		self.file = file

	def __enter__(self):
		self.scene = load_scene(self.file.path)
		print("========================================================")
		print("Transferring {}...".format(self.file.path))
		return self.__find_matches()

	def __exit__(self, exc_type, exc_value, exc_traceback):
		unload_scene(self.scene)
		print("Finished transferring {}".format(self.file.path))
		print("========================================================")