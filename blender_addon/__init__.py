import bpy, os

from .build import AssetBuilder
from .layers import *

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

# Show stuff in the "build" folder in the Asset Library
def setup_asset_library() -> None:
	blender_db = os.environ.get("SG_BLEND_DB")
	build_folder = os.path.join(blender_db, "build")
	prefs = bpy.context.preferences
	lib_name = "Shitgrid Builds"

	# Don't add the same library twice
	for lib in prefs.filepaths.asset_libraries:
		if lib.name == lib_name:
			return

	bpy.ops.preferences.asset_library_add(directory=build_folder)
	sg_lib = prefs.filepaths.asset_libraries[-1]
	sg_lib.name = lib_name

# Tags a data block with custom data used to link it with an asset, layer and version
def tag_data(data, name: str, layer: str, version: int) -> None:
	old_name = data.get("sg_asset")
	old_layer = data.get("sg_layer")
	if not old_name:
		# New data, set all properties
		data["sg_asset"] = name
		data["sg_layer"] = layer
		data["sg_version"] = version
	elif old_name == name and old_layer == layer:
		# Updated data, change version
		data["sg_version"] = version

# Usually artists stay in one layer (department specific)
# Store layer as an addon pref so it stays between restarts
class Preferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	layer: bpy.props.IntProperty(name="Layer", default=0)
	dev_mode: bpy.props.BoolProperty(name="Developer Mode", default=False)

	def draw(self, context):
		self.layout.prop(self, "dev_mode")

# Properties for this plugin shown in the UI
class Properties(bpy.types.PropertyGroup):
	def get_layer(self):
		prefs = bpy.context.preferences
		return prefs.addons[__name__].preferences.layer

	def set_layer(self, value):
		prefs = bpy.context.preferences
		prefs.addons[__name__].preferences.layer = value

	# Publish properties
	layer: bpy.props.EnumProperty(name="Layer", items=layer_menu, get=get_layer, set=set_layer)
	publish_asset: bpy.props.StringProperty(name="Asset Name")

	# Fetch properties
	fetch_asset: bpy.props.StringProperty(name="Asset Name")

	# Developer properties
	dev_make_folder: bpy.props.BoolProperty(name="(DEV) Make folder if missing")
	dev_build_asset: bpy.props.StringProperty(name="Asset Name")
	dev_build_version: bpy.props.IntProperty(name="Layer Version", default=1)
	dev_build_layer: bpy.props.EnumProperty(name="Build Layer", items=layer_menu)

class Publish_Operator(bpy.types.Operator):
	"""Save and increment the version of the above assets"""
	bl_idname = "pipeline.publish"
	bl_label = "Publish Asset"

	def execute(self, context):
		blender_db = os.environ.get("SG_BLEND_DB")
		props = context.scene.sg_props

		if not props.layer:
			self.report({"ERROR_INVALID_INPUT"}, "Please select a layer!")
			return {"CANCELLED"}
		if not props.publish_asset:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in an asset!")
			return {"CANCELLED"}

		wip_folder = os.path.join(blender_db, "wip", props.publish_asset)
		if not os.path.exists(wip_folder):
			if props.dev_make_folder:
				os.makedirs(wip_folder)
			else:
				self.report({"ERROR"}, f"Folder for '{props.publish_asset}' doesn't exist yet! Add it on the website.")
				return {"CANCELLED"}

		# Structure is "master/wip/asset/layer/asset_layer_v001.blend" for now
		layer_folder = os.path.join(wip_folder, props.layer)
		if not os.path.exists(layer_folder):
			os.mkdir(layer_folder)

		# Up version number based on file index in subfolder
		version = len([p for p in os.listdir(layer_folder) if p.endswith(".blend")]) + 1

		# Name is "asset_layer_v001.blend" for now
		file_name = f"{props.publish_asset}_{props.layer}_v{version:03d}.blend"
		path = os.path.join(layer_folder, file_name)

		# I'm using custom data to associate data blocks with an asset, version and layer
		# First tag all collections and objects which haven't already been tagged
		root = context.scene.collection
		for col in root.children_recursive:
			tag_data(col, props.publish_asset, props.layer, version)
		for obj in root.all_objects:
			tag_data(obj, props.publish_asset, props.layer, version)

		# Next tag sub-object data blocks
		for data_type in layer_lookup[props.layer].trigger_update:
			for block in getattr(bpy.data, data_type):
				tag_data(block, props.publish_asset, props.layer, version)

		# Save a copy in the "wip" folder, this copy should never be touched!
		bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=True, copy=True)

		# Would be nice to add a popup for this
		success_msg = f"Published {props.publish_asset} {props.layer} version {version}!"
		self.report({"INFO"}, success_msg)

		return {"FINISHED"}

class Publish_Panel(bpy.types.Panel):
	bl_label = "Publish"
	bl_idname = "ALA_PT_Shitgrid_Publish"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		# This can't be done in register(), so dumping it here for now
		setup_asset_library()

		scn = context.scene
		self.layout.prop(scn.sg_props, "publish_asset")
		self.layout.prop(scn.sg_props, "layer")

		# Developer-only option
		if context.preferences.addons[__name__].preferences.dev_mode:
			self.layout.prop(scn.sg_props, "dev_make_folder")

		self.layout.operator(Publish_Operator.bl_idname, icon="EXPORT")

def get_selected_names(context):
	# Default to all visible objects if none are selected
	selected = context.selected_objects
	objects = selected if selected else context.visible_objects
	names = set()
	for obj in objects:
		name = obj.get("sg_asset")
		if name:
			names.add(name)
	return names

class Check_Updates_Operator(bpy.types.Operator):
	"""Check if asset updates are available"""
	bl_idname = "pipeline.check_updates"
	bl_label = "Check for Asset Updates"

	def execute(self, context):
		blender_db = os.environ.get("SG_BLEND_DB")
		name_set = get_selected_names(context)

		for layer in listed_layers:
			for category in layer.trigger_update:

				block = getattr(bpy.data, category)
				name = block.get("sg_asset")
				# Blocks without sg_asset get skipped here too
				if name not in name_set:
					continue

				layer = block.get("sg_layer")
				folder = os.path.join(blender_db, "wip", asset, layer)
				if not os.path.exists(folder):
					continue

				current = block.get("sg_version")
				latest = len([p for p in os.listdir(folder) if p.endswith(".blend")]) + 1

				print(f"Current: {current}, Latest: {latest}")
				if latest > current:
					print("OUT OF DATE")

		return {"FINISHED"}

class Update_Panel(bpy.types.Panel):
	bl_label = "Update"
	bl_idname = "ALA_PT_Shitgrid_Update"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		name_set = get_selected_names(context)
		names = ", ".join(name_set) if name_set else "None found"
		label = names if selected else f"All ({names})"

		self.layout.label(text=f"Selected: {label}")
		self.layout.operator(Check_Updates_Operator.bl_idname, icon="FILE_REFRESH")

class Fetch_Operator(bpy.types.Operator):
	"""Fetch the latest approved asset build"""
	bl_idname = "pipeline.fetch"
	bl_label = "Fetch Asset"

	def execute(self, context):
		blender_db = os.environ.get("SG_BLEND_DB")
		props = context.scene.sg_props

		if not props.fetch_asset:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in an asset!")
			return {"CANCELLED"}

		build_folder = os.path.join(blender_db, "build", props.fetch_asset)
		if not os.path.exists(build_folder):
			self.report({"ERROR"}, f"Build folder for '{props.fetch_asset}' doesn't exist yet!")
			return {"CANCELLED"}

		# Sort by name to retrieve correct version order
		versions = sorted([os.path.join(build_folder, f) for f in os.listdir(build_folder) if f.endswith(".blend")])
		if not versions:
			self.report({"ERROR"}, f"Builds for '{props.fetch_asset}' don't exist yet!")
			return {"CANCELLED"}

		# Assume top collection is the root we need to import
		latest_path = versions[-1]
		with bpy.data.libraries.load(latest_path, link=False) as (source_data, target_data):
			target_data.collections = [source_data.collections[0]]

		# Add to our Scene Collection
		for col in target_data.collections:
			context.scene.collection.children.link(col)

		return {"FINISHED"}

class Fetch_Panel(bpy.types.Panel):
	bl_label = "Fetch"
	bl_idname = "ALA_PT_Shitgrid_Fetch"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		scn = context.scene
		self.layout.prop(scn.sg_props, "fetch_asset")
		self.layout.operator(Fetch_Operator.bl_idname, icon="IMPORT")

class Dev_Build_Base_Operator(bpy.types.Operator):
	"""Loads clean base geometry from modelling"""
	bl_idname = "pipeline.build_base"
	bl_label = "Load Base Geometry"

	def execute(self, context):
		props = context.scene.sg_props
		try:
			builder = AssetBuilder(props.dev_build_asset)
			builder.process(LayerBase, props.dev_build_version)
			return {"FINISHED"}
		except Exception as err:
			self.report({"ERROR"}, str(err))
			return {"CANCELLED"}

class Dev_Build_Layer_Operator(bpy.types.Operator):
	"""Transfers data from the selected layer onto the asset"""
	bl_idname = "pipeline.build_layer"
	bl_label = "Build Selected Layer"
	
	def execute(self, context):
		props = context.scene.sg_props
		try:
			builder = AssetBuilder(props.dev_build_asset)
			builder.process(layer_lookup[props.dev_build_layer], props.dev_build_version)
			return {"FINISHED"}
		except Exception as err:
			self.report({"ERROR"}, str(err))
			return {"CANCELLED"}

class Build_Panel(bpy.types.Panel):
	bl_label = "(DEV) Build"
	bl_idname = "ALA_PT_Shitgrid_Build"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		scn = context.scene
		self.layout.prop(scn.sg_props, "dev_build_asset")
		self.layout.prop(scn.sg_props, "dev_build_version")
		self.layout.operator(Dev_Build_Base_Operator.bl_idname)
		self.layout.prop(scn.sg_props, "dev_build_layer")
		self.layout.operator(Dev_Build_Layer_Operator.bl_idname)

	@classmethod
	def poll(self, context):
		return context.preferences.addons[__name__].preferences.dev_mode

# Dump all classes to register in here
classes = [
	Publish_Panel, Update_Panel, Fetch_Panel, Build_Panel,
	Publish_Operator, Check_Updates_Operator, Fetch_Operator, Dev_Build_Base_Operator, Dev_Build_Layer_Operator,
	Properties, Preferences
]

def register() -> None:
	if "SG_BLEND_DB" not in os.environ:
		print("ERROR: Missing environment variable SG_BLEND_DB!")
		return

	for cls in classes:
		bpy.utils.register_class(cls)

	scn = bpy.types.Scene
	scn.sg_props = bpy.props.PointerProperty(type=Properties)

def unregister() -> None:
	scn = bpy.types.Scene
	del scn.sg_props
	
	for cls in classes:
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()