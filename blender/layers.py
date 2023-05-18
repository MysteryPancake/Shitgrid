import bpy

from .transfer_map import TransferMap
from .utils import *
from .utils_kitsu import *

class LayerBase:
	"""
	# BASE LAYER
	The deepest build layer, unlisted and only used when headlessly building.\n
	Rips stuff from modelling without materials, rigs, etc.\n
	This will be obsolete and removed once LayerModelling is done.
	"""
	folder = "models"
	blacklist = {"LIGHT", "LIGHT_PROBE", "ARMATURE", "CAMERA", "SPEAKER"}

	@staticmethod
	def process(file: SourceFile):
		# Can't import Scene Collections, so import the whole scene instead
		scene = load_scene(file.path)

		for obj in scene.collection.all_objects:
			# Remove non-modelling objects
			if obj.type in __class__.blacklist:
				bpy.data.objects.remove(obj)
				continue

			# Wipe animation data
			obj.animation_data_clear()

			# Wipe materials
			obj.active_material_index = 0
			for _ in range(len(obj.material_slots)):
				bpy.ops.object.material_slot_remove({"object": obj})

		# Transfer top level collections and objects, children copy automatically
		for obj in scene.collection.objects:
			bpy.context.scene.collection.objects.link(obj)
		for col in scene.collection.children:
			bpy.context.scene.collection.children.link(col)

		# Done copying, remove the imported scene
		unload_scene(scene)

class LayerModelling:
	"""
	# MODELLING LAYER
	TODO
	"""
	folder = "models"
	label = "(TODO) Modelling"
	# Sub-object data blocks which could be part of this layer
	trigger_update = [
		"fonts", "lattices", "metaballs", "meshes", "volumes", "curves", "grease_pencils",
		"paint_curves", "hair_curves", "particles", "pointclouds", "shape_keys"
	]

	@staticmethod
	def process(file: SourceFile):
		print("TODO")
		# TODO

# ========================================================================

# ========================================================================
class LayerMaterials:
	"""
	# MATERIALS LAYER
	Transfers materials and UVs between source and target objects.\n
	I stole all the transferring code from Kitsu :)
	"""
	folder = "materials"
	label = "Surfacing / UVs"
	# Sub-object data blocks which could be part of this layer
	trigger_update = [
		"materials", "textures", "images", "brushes", "palettes", "linestyles"
	]
	
	@staticmethod
	def process(file: SourceFile):
		depsgraph = bpy.context.evaluated_depsgraph_get()

		with TransferMap(file, False) as map:
			for obj_target, obj_source in map.matching_objs.items():

				# Wipe our material slots
				while len(obj_target.material_slots) > len(obj_source.material_slots):
					obj_target.active_material_index = 0
					bpy.ops.object.material_slot_remove({"object": obj_target})

				# Transfer material slots
				for idx in range(len(obj_source.material_slots)):
					if idx >= len(obj_target.material_slots):
						bpy.ops.object.material_slot_add({"object": obj_target})
					obj_target.material_slots[idx].link = obj_source.material_slots[idx].link
					obj_target.material_slots[idx].material = obj_source.material_slots[idx].material

				# Transfer active material slot
				obj_target.active_material_index = obj_source.active_material_index

				# Transfer material slot assignments for curve
				if obj_target.type == "CURVE":
					if not obj_target.data.splines:
						print(f"Curve object '{obj_target.name}' has empty object data")
						continue
					for spl_to, spl_from in zip(obj_target.data.splines, obj_source.data.splines):
						spl_to.material_index = spl_from.material_index

				# Rest of the code applies to meshes only
				if obj_target.type != "MESH":
					continue

				if not obj_target.data.vertices:
					print(f"Mesh object '{obj_target.name}' has empty object data")
					continue

				topo_match = match_topology(obj_source, obj_target)
				if not topo_match:
					print(f"Mismatching topology, falling back to proximity transfer. (Object '{obj_target.name}')")

				# Transfer face data
				if topo_match:
					for pol_to, pol_from in zip(obj_target.data.polygons, obj_source.data.polygons):
						pol_to.material_index = pol_from.material_index
						pol_to.use_smooth = pol_from.use_smooth
				else:
					obj_source_eval = obj_source.evaluated_get(depsgraph)
					for pol_target in obj_target.data.polygons:
						(hit, loc, norm, face_index) = obj_source_eval.closest_point_on_mesh(pol_target.center)
						pol_source = obj_source_eval.data.polygons[face_index]
						pol_target.material_index = pol_source.material_index
						pol_target.use_smooth = pol_source.use_smooth

				# Transfer UV Seams
				if topo_match:
					for edge_from, edge_to in zip(obj_source.data.edges, obj_target.data.edges):
						edge_to.use_seam = edge_from.use_seam
				else:
					bpy.ops.object.data_transfer(
						{
							"object": obj_source,
							"selected_editable_objects": [obj_target],
						},
						data_type="SEAM",
						edge_mapping="NEAREST",
						mix_mode="REPLACE",
					)

				# Wipe our UV layers
				while obj_target.data.uv_layers:
					obj_target.data.uv_layers.remove(obj_target.data.uv_layers[0])

				# Transfer UV layers
				if topo_match:
					for uv_from in obj_source.data.uv_layers:
						uv_to = obj_target.data.uv_layers.new(name=uv_from.name, do_init=False)
						for loop in obj_target.data.loops:
							uv_to.data[loop.index].uv = uv_from.data[loop.index].uv
				else:
					for uv_from in obj_source.data.uv_layers:
						uv_to = obj_target.data.uv_layers.new(name=uv_from.name, do_init=False)
						transfer_corner_data(obj_source, obj_target, uv_from.data, uv_to.data, data_suffix="uv")

				# Make sure correct layer is active
				for uv_l in obj_source.data.uv_layers:
					if uv_l.active_render:
						obj_target.data.uv_layers[uv_l.name].active_render = True
						break

				# Wipe our vertex colors
				while obj_target.data.vertex_colors:
					obj_target.data.vertex_colors.remove(obj_target.data.vertex_colors[0])

				# Transfer vertex colors
				if topo_match:
					for vcol_from in obj_source.data.vertex_colors:
						vcol_to = obj_target.data.vertex_colors.new(name=vcol_from.name, do_init=False)
						for loop in obj_target.data.loops:
							vcol_to.data[loop.index].color = vcol_from.data[loop.index].color
				else:
					for vcol_from in obj_source.data.vertex_colors:
						vcol_to = obj_target.data.vertex_colors.new(name=vcol_from.name, do_init=False)
						transfer_corner_data(obj_source, obj_target, vcol_from.data, vcol_to.data, data_suffix="color")

				# Set 'PREVIEW' vertex color layer as active
				for idx, vcol in enumerate(obj_target.data.vertex_colors):
					if vcol.name == "PREVIEW":
						obj_target.data.vertex_colors.active_index = idx
						break

				# Set 'Baking' or 'UVMap' UV layer as active
				for idx, uvlayer in enumerate(obj_target.data.uv_layers):
					if uvlayer.name == "Baking":
						obj_target.data.uv_layers.active_index = idx
						break
					elif uvlayer.name == "UVMap":
						obj_target.data.uv_layers.active_index = idx

				# Select preview texture as active if found
				for mslot in obj_target.material_slots:
					if not mslot.material or not mslot.material.node_tree:
						continue
					for node in mslot.material.node_tree.nodes:
						if not node.type == "TEX_IMAGE" or not node.image:
							continue
						if "preview" in node.image.name:
							mslot.material.node_tree.nodes.active = node
							break

class LayerGrooming:
	"""
	# GROOMING LAYER
	TODO
	"""
	folder = "grooms"
	label = "(TODO) Grooming"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["hair_curves"]

	@staticmethod
	def process(file: SourceFile):
		print("TODO")
		# TODO

class LayerRigging:
	"""
	# RIGGING LAYER
	TODO
	"""
	folder = "rigs"
	label = "(TODO) Rigging"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["armatures", "shape_keys"]

	@staticmethod
	def process(file: SourceFile):
		print("TODO")
		# TODO

class LayerAssembly:
	"""
	# ASSEMBLY LAYER
	TODO
	"""
	folder = "assembly"
	label = "(TODO) Assembly / Layout"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["cameras"]

	@staticmethod
	def process(file: SourceFile):
		print("TODO")
		# TODO

class LayerAnimation:
	"""
	# ANIMATION LAYER
	TODO
	"""
	folder = "anims"
	label = "(TODO) Animation"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["actions", "shape_keys"]

	@staticmethod
	def process(file: SourceFile):
		print("TODO")
		# TODO

class LayerLighting:
	"""
	# LIGHTING LAYER
	Adds, removes and transfers lights into the current scene.\n
	I wrote this layer myself, hopefully it doesn't explode.
	"""
	folder = "lights"
	label = "Lighting"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["lights", "lightprobes"]

	@staticmethod
	def process(file: SourceFile):
		with TransferMap(file, True) as map:
			# Transfer new lights
			for obj in map.new_objs:
				if obj.type != "LIGHT" and obj.type != "LIGHT_PROBE":
					continue
				# Rebuild collection hierarchy
				parent = map.rebuild_collection_parents(obj)
				parent.objects.link(obj)
			
			# Remove deleted lights
			for obj in map.deleted_objs:
				if obj.type != "LIGHT" and obj.type != "LIGHT_PROBE":
					continue
				bpy.data.objects.remove(obj)
			map.remove_blank_collections()
			
			# Transfer data between lights
			for obj_target, obj_source in map.matching_objs.items():
				if obj_target.type != "LIGHT" and obj_target.type != "LIGHT_PROBE":
					continue
				copy_transform(obj_source, obj_target)
				copy_parenting(obj_source, obj_target)
				copy_attributes(obj_source, obj_target)
				copy_drivers(obj_source, obj_target)

listed_layers = [LayerModelling, LayerMaterials, LayerGrooming, LayerRigging, LayerAssembly, LayerAnimation, LayerLighting]

# For easier data access
layer_menu = []
layer_lookup = {}
for layer in listed_layers:
	layer_menu.append((layer.folder, layer.label, ""))
	layer_lookup[layer.folder] = layer