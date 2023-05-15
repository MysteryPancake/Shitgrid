import bpy

from .transfer_map import TransferMap
from .utils import *

# ========================================================================
# BASE LAYER
# The deepest build layer, unlisted and only used when headlessly building
# Rips stuff from modelling without materials, rigs, etc
# ========================================================================
class LayerBase:
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

# ========================================================================
# MODELLING LAYER
# ========================================================================
class LayerModelling:
	folder = "models"
	label = "Modelling"
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
# MATERIALS LAYER
# Transfers materials between objects within the active scene
# Mostly stolen from Kitsu's codebase :)
# ========================================================================
class LayerMaterials:
	folder = "materials"
	label = "Surfacing / UVs"
	# Sub-object data blocks which could be part of this layer
	trigger_update = [
		"materials", "textures", "images", "brushes", "palettes", "linestyles"
	]
	
	@staticmethod
	def process(file: SourceFile):
		with TransferMap(file) as lookup:
			for us, them in lookup.items():
				# Wipe our material slots
				while len(us.material_slots) > len(them.material_slots):
					us.active_material_index = 0
					bpy.ops.object.material_slot_remove({"object": us})

				# Transfer material slots
				for idx in range(len(them.material_slots)):
					if idx >= len(us.material_slots):
						bpy.ops.object.material_slot_add({"object": us})
					us.material_slots[idx].link = them.material_slots[idx].link
					us.material_slots[idx].material = them.material_slots[idx].material

				# Transfer active material slot
				us.active_material_index = them.active_material_index

				if us.type == "CURVE":
					# Transfer curve material
					for spl_to, spl_from in zip(us.data.splines, them.data.splines):
						spl_to.material_index = spl_from.material_index

				elif us.type == "MESH":
					# Transfer face data
					for pol_to, pol_from in zip(us.data.polygons, them.data.polygons):
						pol_to.material_index = pol_from.material_index
						pol_to.use_smooth = pol_from.use_smooth

					# Transfer UV seams
					for edge_to, edge_from in zip(us.data.edges, them.data.edges):
						edge_to.use_seam = edge_from.use_seam

					# Wipe our UV layers
					while len(us.data.uv_layers) > 0:
						us.data.uv_layers.remove(us.data.uv_layers[0])

					# Transfer UV layers
					for uv_from in them.data.uv_layers:
						uv_to = us.data.uv_layers.new(name=uv_from.name, do_init=False)
						for loop in us.data.loops:
							uv_to.data[loop.index].uv = uv_from.data[loop.index].uv

					# Make sure correct UV layer is active
					for uv_l in them.data.uv_layers:
						if uv_l.active_render:
							us.data.uv_layers[uv_l.name].active_render = True
							break

					# Wipe our vertex colors
					while len(us.data.vertex_colors) > 0:
						us.data.vertex_colors.remove(us.data.vertex_colors[0])

					# Transfer vertex colors
					for vcol_from in them.data.vertex_colors:
						vcol_to = us.data.vertex_colors.new(name=vcol_from.name, do_init=False)
						for loop in us.data.loops:
							vcol_to.data[loop.index].color = vcol_from.data[loop.index].color

# ========================================================================
# GROOMING LAYER
# ========================================================================
class LayerGrooming:
	folder = "grooms"
	label = "Grooming"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["hair_curves"]

	@staticmethod
	def process(file: SourceFile):
		print("TODO")
		# TODO

# ========================================================================
# RIGGING LAYER
# ========================================================================
class LayerRigging:
	folder = "rigs"
	label = "Rigging"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["armatures", "shape_keys"]

	@staticmethod
	def process(file: SourceFile):
		print("TODO")
		# TODO

# ========================================================================
# ASSEMBLY LAYER
# ========================================================================
class LayerAssembly:
	folder = "assembly"
	label = "Assembly / Layout"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["cameras"]

	@staticmethod
	def process(file: SourceFile):
		print("TODO")
		# TODO

# ========================================================================
# ANIMATIONS LAYER
# ========================================================================
class LayerAnimation:
	folder = "anims"
	label = "Animation"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["actions", "shape_keys"]

	@staticmethod
	def process(file: SourceFile):
		print("TODO")
		# TODO

# ========================================================================
# LIGHTING LAYER
# ========================================================================
class LayerLighting:
	folder = "lights"
	label = "Lighting"
	# Sub-object data blocks which could be part of this layer
	trigger_update = ["lights", "lightprobes"]

	@staticmethod
	def process(file: SourceFile):
		print("TODO")
		# TODO

build_order = [LayerModelling, LayerMaterials, LayerGrooming, LayerRigging, LayerAssembly, LayerAnimation, LayerLighting]

# For easier data access
layer_menu = []
layer_lookup = {}
for layer in build_order:
	layer_menu.append((layer.folder, layer.label, ""))
	layer_lookup[layer.folder] = layer