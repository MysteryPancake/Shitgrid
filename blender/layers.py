import bpy
from abc import ABCMeta, abstractmethod

from .transfer_map import *
from .utils import *
from .utils_kitsu import *

# Required properties for all layer classes
class LayerBase(ABCMeta):
	folder: str = NotImplemented
	label: str = NotImplemented
	trigger_update: "list[str]" = NotImplemented
	find_parents: bool = True

	@staticmethod
	@abstractmethod
	def process(map: TransferMap, settings: TransferSettings):
		pass

class LayerModelling(LayerBase):
	"""
	# MODELLING LAYER
	Adds, removes and transfers models into the current scene.
	I stole most of the transferring code from Kitsu :)
	"""
	folder = "models"
	label = "Modelling"
	# Sub-object data blocks which could be part of this layer
	trigger_update = [
		"fonts", "lattices", "metaballs", "meshes", "volumes", "curves", "grease_pencils",
		"paint_curves", "hair_curves", "particles", "pointclouds", "shape_keys"
	]
	object_blacklist = {"LIGHT", "LIGHT_PROBE", "ARMATURE", "CAMERA", "SPEAKER"}

	@staticmethod
	def process(map: TransferMap, settings: TransferSettings):
		# Handle new models
		for obj in map.new_objs:
			if obj.type in __class__.object_blacklist:
				continue

			# Wipe animation data
			obj.animation_data_clear()

			# Wipe materials
			obj.active_material_index = 0
			for _ in range(len(obj.material_slots)):
				bpy.ops.object.material_slot_remove({"object": obj})

			# Wipe shape keys, these belong in rigging
			if hasattr(obj.data, "shape_keys"):
				obj.shape_key_clear()
			
			# Wipe vertex groups, these belong in rigging
			if obj.vertex_groups:
				obj.vertex_groups.clear()

			# Rebuild collection hierarchy
			parent = map.rebuild_collection_parents(obj)
			parent.objects.link(obj)

			# Transfer modifiers
			remap_new_modifiers(obj, map)
			rebind_modifiers(obj)

		# Handle deleted models
		for obj in map.deleted_objs:
			if obj.type in __class__.object_blacklist:
				continue
			bpy.data.objects.remove(obj)
		map.remove_blank_collections()

		# Handle matching models
		for obj_target, obj_source in map.matching_objs.items():
			
			# Copy world space transform
			if settings.update_transform:
				copy_transform(obj_source, obj_target)

			topo_match = match_topology(obj_source, obj_target)
			if topo_match:
				if obj_target.type == "MESH":
					# Transfer position attribute (keeping shapekeys intact)
					if not obj_target.data.vertices:
						print(f"WARNING: Mesh object '{obj_target.name}' has empty object data")
						continue
					offset = [obj_source.data.vertices[i].co - obj_target.data.vertices[i].co for i in range(len(obj_source.data.vertices))]
					offset_sum = 0
					for x in offset:
						offset_sum += x.length
					offset_avg = offset_sum / len(offset)
					if offset_avg > 0.1:
						print(f"Average vertex offset is {offset_avg} for {obj_target.name}")

					for i, vec in enumerate(offset):
						obj_target.data.vertices[i].co += vec

					# Update shapekeys
					if obj_target.data.shape_keys:
						for key in obj_target.data.shape_keys.key_blocks:
							for i, point in enumerate([dat.co for dat in key.data]):
								key.data[i].co = point + offset[i]

				elif obj_target.type == "CURVE":
					# TODO: Geometry transfer for curves
					obj_target_original = bpy.data.objects.new(f"{obj_target.name}.original", obj_target.data)
					# This overrides material data
					obj_target.data = obj_source.data
					# Try to restore material data (slow)
					if not settings.replacing_materials:
						transfer_surfacing(obj_target_original, obj_target, topo_match)
					bpy.data.objects.remove(obj_target_original)
			else:
				# If topology doesn't match, replace object data and proximity transfer shapekeys
				print(f"WARNING: Topology Mismatch! Replacing object data and transferring with potential data loss on '{obj_target.name}'")

				obj_target_original = bpy.data.objects.new(f"{obj_target.name}.original", obj_target.data)
				sk_original = None
				has_keys = hasattr(obj_target.data, "shape_keys") and obj_target.data.shape_keys
				if has_keys:
					sk_original = obj_target.data.shape_keys.copy()
				bpy.context.scene.collection.objects.link(obj_target_original)

				# This overrides material data
				obj_target.data = obj_source.data
				# Try to restore material data (slow)
				if not settings.replacing_materials:
					transfer_surfacing(obj_target_original, obj_target, topo_match)

				if obj_target_original.vertex_groups:
					# Transfer vertex groups
					bpy.ops.object.data_transfer(
						{
							"object": obj_target_original,
							"active_object": obj_target_original,
							"selected_editable_objects": [obj_target],
						},
						data_type="VGROUP_WEIGHTS",
						use_create=True,
						vert_mapping='POLYINTERP_NEAREST',
						layers_select_src="ALL",
						layers_select_dst="NAME",
						mix_mode="REPLACE",
					)
				
				if has_keys:
					# Transfer shapekeys
					transfer_shapekeys_proximity(obj_target_original, obj_target)
					# Transfer shapekey drivers
					copy_drivers(sk_original, obj_target.data.shape_keys)
					del sk_original

				bpy.data.objects.remove(obj_target_original)

			# Remove old modifiers
			# UPDATE: For now, don't remove any

			#for mod in obj_target.modifiers:
				#if mod.name not in __class__.modifier_whitelist and mod.name not in [m.name for m in obj_source.modifiers]:
					#print(f"Removing modifier {mod.name}")
					#obj_target.modifiers.remove(mod)
			
			# Transfer modifiers
			transfer_new_modifiers(obj_source, obj_target)
			remap_modifiers(obj_source, obj_target, map)
			rebind_modifiers(obj_target)

			# Ensure object version matches
			transfer_version(obj_source, obj_target)
			# Ensure mesh version matches
			transfer_version(obj_source.data, obj_target.data)

class LayerMaterials(LayerBase):
	"""
	# MATERIALS LAYER
	Transfers materials and UVs between source and target objects.\n
	I stole most of the transferring code from Kitsu :)
	"""
	folder = "materials"
	label = "Surfacing / UVs"
	# Sub-object data blocks which could be part of this layer
	trigger_update = [
		"materials", "textures", "images", "brushes", "palettes"
	]
	# This layer doesn't need parents, skip calculating it
	find_parents = False
	
	@staticmethod
	def process(map: TransferMap, settings: TransferSettings):
		# Handle matching materials
		for obj_target, obj_source in map.matching_objs.items():
			topo_match = match_topology(obj_source, obj_target)
			if not topo_match:
				print(f"WARNING: Mismatching topology, falling back to proximity transfer. (Object '{obj_target.name}')")
			transfer_surfacing(obj_source, obj_target, topo_match)

class LayerGrooming(LayerBase):
	"""
	# GROOMING LAYER
	TODO
	"""
	folder = "grooms"
	label = "(TODO) Grooming"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["hair_curves"]

	@staticmethod
	def process(map: TransferMap, settings: TransferSettings):
		print("TODO")
		# TODO

class LayerRigging(LayerBase):
	"""
	# RIGGING LAYER
	TODO
	"""
	folder = "rigs"
	label = "(TODO) Rigging / Shape Keys / Vertex Groups"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["armatures", "shape_keys"]

	@staticmethod
	def process(map: TransferMap, settings: TransferSettings):
		print("TODO")
		# TODO

class LayerAssembly(LayerBase):
	"""
	# ASSEMBLY LAYER
	TODO
	"""
	folder = "assembly"
	label = "(TODO) Assembly / Layout"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["cameras"]

	@staticmethod
	def process(map: TransferMap, settings: TransferSettings):
		print("TODO")
		# TODO

class LayerAnimation(LayerBase):
	"""
	# ANIMATION LAYER
	TODO
	"""
	folder = "anims"
	label = "(TODO) Animation"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["actions", "shape_keys"]

	@staticmethod
	def process(map: TransferMap, settings: TransferSettings):
		print("TODO")
		# TODO

class LayerLighting(LayerBase):
	"""
	# LIGHTING LAYER
	Adds, removes and transfers lights into the current scene.
	"""
	folder = "lights"
	label = "Lighting"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["lights", "lightprobes", "worlds"]

	@staticmethod
	def process(map: TransferMap, settings: TransferSettings):
		# Handle new lights
		for obj in map.new_objs:
			if obj.type != "LIGHT" and obj.type != "LIGHT_PROBE":
				continue
			# Rebuild collection hierarchy
			parent = map.rebuild_collection_parents(obj)
			parent.objects.link(obj)
		
		# Handle deleted lights
		for obj in map.deleted_objs:
			if obj.type != "LIGHT" and obj.type != "LIGHT_PROBE":
				continue
			bpy.data.objects.remove(obj)
		map.remove_blank_collections()
		
		# Handle matching lights
		for obj_target, obj_source in map.matching_objs.items():
			if obj_target.type != "LIGHT" and obj_target.type != "LIGHT_PROBE":
				continue
			if settings.update_transform:
				copy_transform(obj_source, obj_target)
			# Transfer the light data and version
			obj_target.data = obj_source.data
			# Ensure object version matches
			transfer_version(obj_source, obj_target)
		
		# Transfer world (copy_attributes doesn't work for some reason)
		bpy.context.scene.world = map.scene.world

listed_layers = [LayerModelling, LayerGrooming, LayerRigging, LayerMaterials, LayerAssembly, LayerAnimation, LayerLighting]

# For easier data access
layer_menu = []
layer_lookup = {}
for layer in listed_layers:
	layer_menu.append((layer.folder, layer.label, ""))
	layer_lookup[layer.folder] = layer