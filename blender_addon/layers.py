import bpy

class Layer_Core:
	# ========================================================================
	# Core is the deepest build layer.
	# The core is the starting point when building any asset.
	# Modelling always goes through this layer.
	# ========================================================================
	blacklist = [
		bpy.data.materials,
		bpy.data.lights,
		bpy.data.brushes,
		bpy.data.lightprobes,
		bpy.data.cameras,
		bpy.data.armatures,
		bpy.data.actions,
		bpy.data.palettes,
		bpy.data.textures,
		bpy.data.images,
		bpy.data.speakers
	]

	@staticmethod
	def process(blend):
		# This assumes clean.py was run before to remove everything.
		# Rename default scene to prevent name conflicts
		bpy.context.scene.name = "TEMPORARY_SCENE"

		# We can't assume artists will use collections, so import scenes instead.
		# Blender doesn't allow importing the Scene Collection, otherwise we could use that.
		with bpy.data.libraries.load(blend, link=False, assets_only=False) as (data_from, data_to):
			data_to.scenes = data_from.scenes

		# Remove the default scene
		bpy.data.scenes.remove(bpy.context.scene)

		# Clear unnecessary data blocks
		for junk in Layer_Core.blacklist:
			for item in junk:
				junk.remove(item)
		bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

class Layer_Model:
	folder = "models"
	label = "Modelling: Models"

class Layer_Material:
	folder = "mats"
	label = "Surfacing: Materials"