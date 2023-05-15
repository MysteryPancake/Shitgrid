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

# Usually artists stay in one layer (department specific)
# Store layer as an addon pref so it stays between restarts
class Preferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	layer: bpy.props.IntProperty(name="Layer", default=0)

layer_items = [
	("models", "Models", ""),
	("materials", "Materials / UVs", ""),
	("rigs", "Rigs", ""),
]

# Show stuff in the "build" folder in the Asset Library
def setup_asset_library() -> None:
	blender_db = os.environ.get("SG_BLEND_DB")
	if not blender_db:
		return

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

# Properties for this plugin shown in the UI
class Properties(bpy.types.PropertyGroup):
	def get_layer(self):
		prefs = bpy.context.preferences
		return prefs.addons[__name__].preferences.layer

	def set_layer(self, value):
		prefs = bpy.context.preferences
		prefs.addons[__name__].preferences.layer = value

	# Publish properties
	layer: bpy.props.EnumProperty(name="Layer", items=layer_items, get=get_layer, set=set_layer)
	publish_asset: bpy.props.StringProperty(name="Asset Name")

	# Fetch properties
	fetch_asset: bpy.props.StringProperty(name="Asset Name")

	# DEV ONLY, REMOVE IN FINAL BUILD!
	make_folder: bpy.props.BoolProperty(name="(DEV) Make asset if it doesn't exist")

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
	bl_label = "Publish Asset"

	def execute(self, context):
		props = context.scene.sg_props
		blender_db = os.environ.get("SG_BLEND_DB")

		if not blender_db:
			self.report({"ERROR"}, "Missing environment variable SG_BLEND_DB!")
			return {"CANCELLED"}

		if not props.layer:
			self.report({"ERROR_INVALID_INPUT"}, "Please select a layer!")
			return {"CANCELLED"}

		if not props.publish_asset:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in an asset!")
			return {"CANCELLED"}

		wip_folder = os.path.join(blender_db, "wip", props.publish_asset)
		if not os.path.exists(wip_folder):
			if props.make_folder:
				# DEV ONLY, REMOVE IN FINAL BUILD!
				os.makedirs(wip_folder)
			else:
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

		# I'm using custom data to associate data blocks with an asset, version and layer
		# First, tag all collections and objects which haven't already been tagged
		root = context.scene.collection
		for col in root.children_recursive:
			tag_data(col, props.publish_asset, props.layer, version)
		for obj in root.all_objects:
			tag_data(obj, props.publish_asset, props.layer, version)

		# Next, tag sub-object data blocks
		if props.layer in update_whitelist:
			for data_type in update_whitelist[props.layer]:
				for block in getattr(bpy.data, data_type):
					tag_data(block, props.publish_asset, props.layer, version)

		# Save a copy in the "wip" folder, this copy should never be touched!
		bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=True, copy=True)

		# Would be nice to add a popup for this
		success_msg = "Published {} {} version {}!".format(props.publish_asset, props.layer, version)
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
		self.layout.prop(scn.sg_props, "make_folder")
		self.layout.operator(Publish_Operator.bl_idname, icon="EXPORT")

class Check_Updates_Operator(bpy.types.Operator):
	"""Check if asset updates are available"""
	bl_idname = "pipeline.check_updates"
	bl_label = "Check for Asset Updates"

	def execute(self, context):
		# TODO
		return {"FINISHED"}

class Update_Panel(bpy.types.Panel):
	bl_label = "Update"
	bl_idname = "ALA_PT_Shitgrid_Update"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def __draw_selected(self, context):
		# Default to all visible objects if none are selected
		selected = context.selected_objects
		objects = selected if selected else context.visible_objects

		name_set = set()
		for obj in objects:
			name = obj.get("sg_asset")
			if name:
				name_set.add(name)
		names = ", ".join(name_set) if name_set else "None found"

		label = names if selected else "All ({})".format(names)
		self.layout.label(text="Selected: {}".format(label))

	def draw(self, context):
		self.__draw_selected(context)
		self.layout.operator(Check_Updates_Operator.bl_idname, icon="FILE_REFRESH")

class Fetch_Operator(bpy.types.Operator):
	"""Fetch the latest approved asset build"""
	bl_idname = "pipeline.fetch"
	bl_label = "Fetch Asset"

	def execute(self, context):
		props = context.scene.sg_props
		blender_db = os.environ.get("SG_BLEND_DB")

		if not blender_db:
			self.report({"ERROR"}, "Missing environment variable SG_BLEND_DB!")
			return {"CANCELLED"}

		if not props.fetch_asset:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in an asset!")
			return {"CANCELLED"}

		build_folder = os.path.join(blender_db, "build", props.fetch_asset)
		if not os.path.exists(build_folder):
			self.report({"ERROR"}, "Build folder for asset {} doesn't exist yet!".format(props.fetch_asset))
			return {"CANCELLED"}

		# Sort by name to retrieve correct version order
		versions = sorted([os.path.join(build_folder, f) for f in os.listdir(build_folder) if f.endswith(".blend")])
		if not versions:
			self.report({"ERROR"}, "Builds for asset {} don't exist yet!".format(props.fetch_asset))
			return {"CANCELLED"}

		# Assume top collection is the root we need to import
		latest_path = versions[-1]
		with bpy.data.libraries.load(latest_path, link=False) as (their_data, our_data):
			our_data.collections = [their_data.collections[0]]

		# Add to our Scene Collection
		for col in our_data.collections:
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

# Dump all classes to register in here
classes = [
	Publish_Panel, Update_Panel, Fetch_Panel,
	Publish_Operator, Check_Updates_Operator, Fetch_Operator,
	Properties, Preferences
]

def register() -> None:
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