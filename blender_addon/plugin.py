import bpy, os

bl_info = {
	"name": "Shitgrid Pipeline",
	"description": "Official Unofficial ALA Pipeline (Sponsored by Ian Hubert)",
	"author": "Animal Logic Academy",
	"version": (1, 0),
	"blender": (3, 4, 1),
	"location": "View 3D > Tool Shelf > Shitgrid",
	"support": "COMMUNITY",
	"category": "ALA",
}

# Store task layer as an addon pref so it stays between restarts
class Preferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	layer: bpy.props.IntProperty(name="Task Layer", default=0)

layer_items = [
	("models", "Models", ""),
	("materials", "Materials / UVs", ""),
	("rigs", "Rigs", ""),
	("lights", "Lights", ""),
]

# This can't be done in register() unfortunately
def setup_asset_library(prefs):
	blender_db = os.environ.get("SHITGRID_BLEND_DB")
	if not blender_db:
		return

	build_folder = os.path.join(blender_db, "build")
	lib_name = "Shitgrid Builds"

	# Don't add the same library twice
	for lib in prefs.filepaths.asset_libraries:
		if lib.name == lib_name:
			return

	# Add and rename library
	bpy.ops.preferences.asset_library_add(directory=build_folder)
	sg_lib = prefs.filepaths.asset_libraries[-1]
	sg_lib.name = lib_name

class Properties(bpy.types.PropertyGroup):
	def get_layer(self):
		prefs = bpy.context.preferences
		setup_asset_library(prefs)
		return prefs.addons[__name__].preferences.layer

	def set_layer(self, value):
		prefs = bpy.context.preferences
		prefs.addons[__name__].preferences.layer = value

	# Publish properties
	layer: bpy.props.EnumProperty(
		name="Task Layer",
		items=layer_items,
		get=get_layer,
		set=set_layer
	)
	publish_asset: bpy.props.StringProperty(name="Asset Name")

# TODO: MAKE SOURCE_FILE A SHARED PYTHON MODULE
# ========================================================================
def add_link(block, asset, layer, version):
	# Only add, don't override
	if block.get("sg_asset"):
		return
	block["sg_asset"] = asset
	block["sg_layer"] = layer
	block["sg_version"] = version
# ========================================================================

# Sub-object data blocks which should trigger a version update when changed
update_whitelist = {
	"models": [
		"fonts", "lattices", "metaballs", "meshes", "volumes", "curves",
		"grease_pencils", "hair_curves", "paint_curves", "particles", "pointclouds"
	],
	"materials": [
		"materials", "textures", "images", "brushes", "palettes", "linestyles"
	]
}

class Publish_Operator(bpy.types.Operator):
	"""Save and increment the version of the above assets"""
	bl_idname = "pipeline.publish"
	bl_label = "Publish"

	def execute(self, context):
		props = context.scene.sg_props

		# Directory for storing published Blender files for building
		blender_db = os.environ.get("SHITGRID_BLEND_DB")
		if not blender_db:
			self.report({"ERROR"}, "Missing environment variable SHITGRID_BLEND_DB!")
			return {"CANCELLED"}

		if not props.layer:
			self.report({"ERROR_INVALID_INPUT"}, "Please select a task layer!")
			return {"CANCELLED"}

		if not props.publish_asset:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in an asset!")
			return {"CANCELLED"}

		# Make sure to set the SHITGRID_BLEND_DB env var or this will break!
		wip_folder = os.path.join(blender_db, "wip", props.publish_asset)
		if not os.path.exists(wip_folder):
			self.report({"ERROR"}, "Asset {} doesn't exist yet! Add it on the website.".format(props.publish_asset))
			return {"CANCELLED"}

		# Structure is "master/wip/asset/layer/asset_layer_v001.blend" for now
		layer_folder = os.path.join(wip_folder, props.layer)
		if not os.path.exists(layer_folder):
			os.mkdir(layer_folder)

		# Up version number based on file index in subfolder
		version = len([p for p in os.listdir(layer_folder) if p.endswith(".blend")]) + 1

		# Name is "asset_layer_v001.blend" for now
		file_name = "{}_{}_v{:03d}.blend".format(props.publish_asset, props.layer, version)
		path = os.path.join(layer_folder, file_name)

		# Add custom data to determine asset link where not already linked
		root = context.scene.collection
		for col in root.children_recursive:
			add_link(col, props.publish_asset, props.layer, version)
		for obj in root.all_objects:
			add_link(obj, props.publish_asset, props.layer, version)
		for data_type in update_whitelist.get(props.layer, []):
			for block in getattr(bpy.data, data_type):
				add_link(block, props.publish_asset, props.layer, version)

		# Save a copy. This copy should never be touched!
		bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=True, copy=True)

		# Would be nice to add a popup box for this
		success_msg = "Published {} {} version {}!".format(props.publish_asset, props.layer, version)
		self.report({"INFO"}, success_msg)

		return {"FINISHED"}

class Publish_Panel(bpy.types.Panel):
	bl_label = "Publish Asset"
	bl_idname = "ALA_PT_Shitgrid_Publish"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		layout = self.layout
		scn = context.scene
		layout.prop(scn.sg_props, "layer")
		layout.prop(scn.sg_props, "publish_asset")
		layout.operator(Publish_Operator.bl_idname)

# Dump all classes to register in here
classes = [Publish_Panel, Publish_Operator, Properties, Preferences]

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	scn = bpy.types.Scene
	scn.sg_props = bpy.props.PointerProperty(type=Properties)

def unregister():
	scn = bpy.types.Scene
	del scn.sg_props
	for cls in classes:
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()