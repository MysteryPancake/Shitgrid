import bpy, os
from uuid import uuid4

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

# TODO: Find somewhere to put this (it won't run in register)
def setup_asset_library() -> None:
	"""Registers the build folder to display in the asset library"""
	blender_db = os.environ.get("SG_BLEND_DB")
	build_folder = os.path.join(blender_db, "build")
	prefs = bpy.context.preferences
	lib_name = "Asset Builds"

	# Don't add the same library twice
	for lib in prefs.filepaths.asset_libraries:
		if lib.name == lib_name:
			return

	bpy.ops.preferences.asset_library_add(directory=build_folder)
	sg_lib = prefs.filepaths.asset_libraries[-1]
	sg_lib.name = lib_name

def tag_data(data, name: str, layer: str, version: int) -> None:
	"""
	Tags a data block with custom data.\n
	This is used to associate everything with an asset, layer and version.\n
	`sg_id` is used for matching. Try to avoid duplicate IDs.\n
	When IDs are duplicated, it links by order.
	"""
	old_name = data.get("sg_asset")
	old_layer = data.get("sg_layer")
	if not old_name:
		# New data, set all properties
		data["sg_asset"] = name
		data["sg_layer"] = layer
		data["sg_version"] = version
		data["sg_id"] = str(uuid4())
	elif old_name == name and old_layer == layer:
		# Updated data, change version
		data["sg_version"] = version

class Preferences(bpy.types.AddonPreferences):
	"""Preferences for this addon"""
	bl_idname = __name__
	dev_mode: bpy.props.BoolProperty(name="Developer Mode", default=False)

	def draw(self, context):
		layout = self.layout
		layout.prop(self, "dev_mode")

class Update_Item(bpy.types.PropertyGroup):
	"""Properties for items displayed in the update list"""
	# Name property is built-in
	asset: bpy.props.StringProperty(name="Asset Name")
	layers: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
	outdated: bpy.props.BoolProperty(default=False)
	checked: bpy.props.BoolProperty(default=True)

class Properties(bpy.types.PropertyGroup):
	"""Properties shown in the UI panel"""
	# Publish properties
	publish_layer: bpy.props.EnumProperty(name="Layer", items=layer_menu)
	publish_asset: bpy.props.StringProperty(name="Asset Name")

	# Fetch properties
	fetch_asset: bpy.props.StringProperty(name="Asset Name")

	# Update properties
	update_items: bpy.props.CollectionProperty(type=Update_Item)
	update_transform: bpy.props.BoolProperty(name="Update Transform", default=True)

	# Developer properties
	dev_make_folder: bpy.props.BoolProperty(name="(DEV) Make asset if missing", default=False)
	dev_build_layer: bpy.props.EnumProperty(name="Layer", items=layer_menu)
	dev_build_version: bpy.props.IntProperty(name="Version", default=1)

def get_transfer_settings(props: Properties):
	"""Builds transfer settings from UI panel properties"""
	settings = TransferSettings()
	settings.update_transform = props.update_transform
	return settings

class Publish_Operator(bpy.types.Operator):
	"""Save and increment the version of the above assets"""
	bl_idname = "pipeline.publish"
	bl_label = "Publish Asset"

	def execute(self, context):
		blender_db = os.environ.get("SG_BLEND_DB")
		props = context.scene.sg_props

		if not props.publish_layer:
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
				self.report({"ERROR"}, f"Asset '{props.publish_asset}' doesn't exist yet! Add it on the website.")
				return {"CANCELLED"}

		# Structure is "master/wip/asset/layer/asset_layer_v001.blend" for now
		layer_folder = os.path.join(wip_folder, props.publish_layer)
		if not os.path.exists(layer_folder):
			os.mkdir(layer_folder)

		# Up version number based on file index in subfolder
		version = len([p for p in os.listdir(layer_folder) if p.endswith(".blend")]) + 1

		# Name is "asset_layer_v001.blend" for now
		file_name = f"{props.publish_asset}_{props.publish_layer}_v{version:03d}.blend"
		path = os.path.join(layer_folder, file_name)

		# I'm using custom data to associate data blocks with an asset, version and layer
		# First tag all collections and objects which haven't already been tagged
		root = context.scene.collection
		for col in root.children_recursive:
			tag_data(col, props.publish_asset, props.publish_layer, version)
		for obj in root.all_objects:
			tag_data(obj, props.publish_asset, props.publish_layer, version)

		# Next tag sub-object data blocks
		for data_type in layer_lookup[props.publish_layer].trigger_update:
			for block in getattr(bpy.data, data_type):
				tag_data(block, props.publish_asset, props.publish_layer, version)

		# Save a copy in the "wip" folder, this copy should never be touched!
		bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=True, copy=True)

		# Would be nice to add a popup for this
		success_msg = f"Published {props.publish_asset} {props.publish_layer} version {version}!"
		self.report({"INFO"}, success_msg)

		return {"FINISHED"}

class Publish_Panel(bpy.types.Panel):
	bl_label = "Publish"
	bl_idname = "ALA_PT_Publish"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		props = context.scene.sg_props
		layout = self.layout
		if context.preferences.addons[__name__].preferences.dev_mode:
			layout.prop(props, "dev_make_folder")
		layout.prop(props, "publish_asset")
		layout.prop(props, "publish_layer")
		layout.operator(Publish_Operator.bl_idname, icon="EXPORT")

def get_selected_assets(context):
	"""Returns names of selected assets, or visible assets when none are selected"""
	objects = context.selected_objects
	if not objects:
		objects = context.visible_objects
	names = set()
	for obj in objects:
		name = obj.get("sg_asset")
		if name:
			names.add(name)
	return names

class Check_Updates_Operator(bpy.types.Operator):
	"""Check if asset updates are available"""
	bl_idname = "pipeline.check_updates"
	bl_label = "Check for Updates"

	def execute(self, context):
		blender_db = os.environ.get("SG_BLEND_DB")
		name_set = get_selected_assets(context)

		# Clear previously listed updates
		props = context.scene.sg_props
		props.update_items.clear()

		# Using a list instead of a set to preserve layer order
		updates: dict[str, list[Any]] = {}
		for asset in name_set:
			updates[asset] = []

		# Find outdated data blocks
		for layer in listed_layers:
			for data_type in layer.trigger_update:
				for block in getattr(bpy.data, data_type):

					asset = block.get("sg_asset")
					# Blocks without sg_asset get skipped here too
					if asset not in name_set:
						continue

					# Don't check outdated layers again
					layer = block.get("sg_layer")
					if layer in updates[asset]:
						continue

					folder = os.path.join(blender_db, "wip", asset, layer)
					if not os.path.exists(folder):
						continue

					current = block.get("sg_version")
					latest = len([p for p in os.listdir(folder) if p.endswith(".blend")])
					if latest > current and layer not in updates[asset]:
						updates[asset].append(layer)

		# Build update list UI
		for asset in name_set:
			layer_order = updates[asset]
			layers = ", ".join(layer_order) if layer_order else "Up to date"

			# Add UI list entry
			item = props.update_items.add()
			item.name = f"{asset} ({layers})"
			item.asset = asset
			for layer_name in layer_order:
				layer = item.layers.add()
				layer.name = layer_name
			item.outdated = bool(layer_order)

		return {"FINISHED"}

class Update_Operator(bpy.types.Operator):
	"""Apply selected updates to assets"""
	bl_idname = "pipeline.update"
	bl_label = "Apply Updates"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		props = context.scene.sg_props
		settings = get_transfer_settings(props)
		try:
			for item in props.update_items:
				# Skip unchecked items
				if not item.checked or not item.outdated:
					continue

				# This assumes correct layer ordering from Check_Updates
				builder = AssetBuilder(item.asset)
				for layer in item.layers:
					layer_obj = layer_lookup[layer.name]
					builder.process(layer_obj, settings, -1)
					
			props.update_items.clear()
			return {"FINISHED"}
		
		except Exception as err:
			self.report({"ERROR"}, str(err))
			return {"CANCELLED"}

class Update_Close_Operator(bpy.types.Operator):
	"""Close updates list"""
	bl_idname = "pipeline.close_update"
	bl_label = "Close"

	def execute(self, context):
		props = context.scene.sg_props
		props.update_items.clear()
		return {"FINISHED"}

class Update_Panel(bpy.types.Panel):
	bl_label = "Update"
	bl_idname = "ALA_PT_Update"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		layout = self.layout
		props = context.scene.sg_props

		# List of selected assets
		name_set = get_selected_assets(context)
		names = ", ".join(name_set) if name_set else "None found"
		label = names if context.selected_objects else f"All ({names})"
		layout.label(text=f"Selected: {label}")

		# Check updates and close button
		if props.update_items:
			layout.operator(Update_Close_Operator.bl_idname, icon="PANEL_CLOSE")
		elif name_set:
			layout.operator(Check_Updates_Operator.bl_idname, icon="FILE_REFRESH")

		if not props.update_items:
			return
		
		# List of available updates
		outdated = False
		update_list = layout.box().column()
		update_list.label(text="Update Status:")
		for item in props.update_items:
			outdated = outdated or item.outdated
			row = update_list.row()
			row.enabled = item.outdated
			row.prop(
				item,
				"checked",
				icon="CHECKBOX_HLT" if item.checked or not item.outdated else "CHECKBOX_DEHLT",
				text="",
				emboss=False
			)
			row.label(text=item.name)

		if outdated:
			# Update button
			layout.operator(Update_Operator.bl_idname, icon="SORT_ASC")
			# Update transform checkbox
			layout.prop(props, "update_transform")

class Fetch_Operator(bpy.types.Operator):
	"""Fetch the latest approved asset build"""
	bl_idname = "pipeline.fetch"
	bl_label = "Fetch Asset"
	bl_options = {"REGISTER", "UNDO"}

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
	bl_idname = "ALA_PT_Fetch"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		props = context.scene.sg_props
		layout = self.layout
		layout.prop(props, "fetch_asset")
		layout.operator(Fetch_Operator.bl_idname, icon="IMPORT")

class Dev_Build_Operator(bpy.types.Operator):
	"""Transfer data from the selected layer onto the asset"""
	bl_idname = "pipeline.build_layer"
	bl_label = "Build Selected Layer"
	bl_options = {"REGISTER", "UNDO"}
	
	def execute(self, context):
		props = context.scene.sg_props
		if not props.fetch_asset:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in an asset!")
			return {"CANCELLED"}
		try:
			builder = AssetBuilder(props.fetch_asset)
			settings = get_transfer_settings(props)
			layer = layer_lookup[props.dev_build_layer]
			builder.process(layer, settings, props.dev_build_version)
			return {"FINISHED"}
		except Exception as err:
			self.report({"ERROR"}, str(err))
			return {"CANCELLED"}

class Build_Panel(bpy.types.Panel):
	bl_label = "(DEV) Build"
	bl_idname = "ALA_PT_Build"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		props = context.scene.sg_props
		layout = self.layout

		layout.use_property_split = True
		layout.use_property_decorate = False
		
		layout.prop(props, "fetch_asset")
		layout.prop(props, "dev_build_layer")
		layout.prop(props, "dev_build_version")
		layout.prop(props, "update_transform")
		layout.operator(Dev_Build_Operator.bl_idname)

	@classmethod
	def poll(cls, context):
		return context.preferences.addons[__name__].preferences.dev_mode

# Dump all classes to register in here
classes = [
	Publish_Panel, Update_Panel, Fetch_Panel, Build_Panel,
	Publish_Operator, Check_Updates_Operator, Update_Operator,
	Update_Close_Operator, Fetch_Operator, Dev_Build_Operator,
	Update_Item, Properties, Preferences
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