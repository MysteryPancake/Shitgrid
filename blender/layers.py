import bpy
from abc import ABCMeta, abstractmethod

from .transfer_map import *
from .utils import *
from .utils_kitsu import *

# Required properties for all layer classes
class LayerBase(ABCMeta):
	folder: str = NotImplemented
	label: str = NotImplemented
	trigger_update: list[str] = NotImplemented
	find_parents: bool = True

	@staticmethod
	@abstractmethod
	def process(map: TransferMap, settings: TransferSettings):
		pass

class LayerModelling(LayerBase):
	"""
	# MODELLING LAYER
	Adds, removes and transfers models into the current scene.
	I stole the transferring code from Kitsu :)
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

			# Rebuild collection hierarchy
			parent = map.rebuild_collection_parents(obj)
			parent.objects.link(obj)

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
				# If topology matches, transfer position attribute (keeping shapekeys intact)
				if obj_target.type == "MESH":
					if not obj_target.data.vertices:
						print(f"WARNING: Mesh object '{obj_target.name}' has empty object data")
						continue
					offset = [obj_source.data.vertices[i].co - obj_target.data.vertices[i].co for i in range(len(obj_source.data.vertices))]
					offset_sum = 0
					for x in offset:
						offset_sum += x.length
					offset_avg = offset_sum / len(offset)
					if offset_avg > 0.1:
						print(f"Average Vertex offset is {offset_avg} for {obj_target.name}")

					for i, vec in enumerate(offset):
						obj_target.data.vertices[i].co += vec

					# Update shapekeys
					if obj_target.data.shape_keys:
						for key in obj_target.data.shape_keys.key_blocks:
							for i, point in enumerate([dat.co for dat in key.data]):
								key.data[i].co = point + offset[i]
				elif obj_target.type == "CURVE":
					# TODO: proper geometry transfer for curves
					obj_target_original = bpy.data.objects.new(f"{obj_target.name}.original", obj_target.data)
					# This overrides material data
					obj_target.data = obj_source.data
					# Try to restore material data
					transfer_surfacing(obj_target_original, obj_target, topo_match)
					bpy.data.objects.remove(obj_target_original)
			else:
				# If topology doesn't match, replace object data and proximity transfer rigging data
				obj_target_original = bpy.data.objects.new(f"{obj_target.name}.original", obj_target.data)
				sk_original = obj_target.data.shape_keys.copy() if obj_target.data.shape_keys else None
				bpy.context.scene.collection.objects.link(obj_target_original)

				print(f"WARNING: Topology Mismatch! Replacing object data and transferring with potential data loss on '{obj_target.name}'")
				# This overrides material data
				obj_target.data = obj_source.data
				# Try to restore material data
				transfer_surfacing(obj_target_original, obj_target, topo_match)

				# Transfer weights
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

				# Transfer shapekeys
				transfer_shapekeys_proximity(obj_target_original, obj_target)

				# Transfer drivers
				copy_drivers(sk_original, obj_target.data.shape_keys)

				del sk_original
				bpy.data.objects.remove(obj_target_original)

			# Remove old modifiers
			# UPDATE: For now, don't remove any

			#for mod in obj_target.modifiers:
				#if mod.name not in __class__.modifier_whitelist and mod.name not in [m.name for m in obj_source.modifiers]:
					#print(f"Removing modifier {mod.name}")
					#obj_target.modifiers.remove(mod)
			
			# Transfer new modifiers
			for i, mod in enumerate(obj_source.modifiers):
				if mod.name in [m.name for m in obj_target.modifiers]:
					continue
				mod_new = obj_target.modifiers.new(mod.name, mod.type)
				# Sort new modifier at correct index (default to beginning of the stack)
				idx = 0
				if i > 0:
					name_prev = obj_source.modifiers[i - 1].name
					for target_mod_i, target_mod in enumerate(obj_target.modifiers):
						if target_mod.name == name_prev:
							idx = target_mod_i + 1
				bpy.ops.object.modifier_move_to_index({"object": obj_target}, modifier=mod_new.name, index=idx)
			
			# Sync modifier settings
			for i, mod_source in enumerate(obj_source.modifiers):
				mod_target = obj_target.modifiers.get(mod_source.name)
				if not mod_target:
					continue
				for prop in [p.identifier for p in mod_source.bl_rna.properties if not p.is_readonly]:
					value = getattr(mod_source, prop)
					if type(value) == bpy.types.Object and value in map.matching_objs_target:
						# Remap modifiers to transferred objects if possible
						value = map.matching_objs_target[value]
					setattr(mod_target, prop, value)
			
			# Rebind modifiers (corrective smooth, surface deform, mesh deform)
			for mod in obj_target.modifiers:
				if mod.type == "SURFACE_DEFORM":
					if not mod.is_bound:
						continue
					for i in range(2):
						bpy.ops.object.surfacedeform_bind({"object": obj_target, "active_object": obj_target}, modifier=mod.name)
				elif mod.type == "MESH_DEFORM":
					if not mod.is_bound:
						continue
					for i in range(2):
						bpy.ops.object.meshdeform_bind({"object": obj_target, "active_object": obj_target}, modifier=mod.name)
				elif mod.type == "CORRECTIVE_SMOOTH":
					if not mod.is_bind:
						continue
					for i in range(2):
						bpy.ops.object.correctivesmooth_bind({"object": obj_target, "active_object": obj_target}, modifier=mod.name)

class LayerMaterials(LayerBase):
	"""
	# MATERIALS LAYER
	Transfers materials and UVs between source and target objects.\n
	I stole the transferring code from Kitsu :)
	"""
	folder = "materials"
	label = "Surfacing / UVs"
	# Sub-object data blocks which could be part of this layer
	trigger_update = [
		"materials", "textures", "images", "brushes", "palettes", "linestyles"
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
	label = "(TODO) Rigging"
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
			copy_attributes(obj_source, obj_target)
			copy_drivers(obj_source, obj_target)
		
		# Transfer world (copy_attributes doesn't work for some reason)
		bpy.context.scene.world = map.scene.world

listed_layers = [LayerModelling, LayerMaterials, LayerGrooming, LayerRigging, LayerAssembly, LayerAnimation, LayerLighting]

# For easier data access
layer_menu = []
layer_lookup = {}
for layer in listed_layers:
	layer_menu.append((layer.folder, layer.label, ""))
	layer_lookup[layer.folder] = layer