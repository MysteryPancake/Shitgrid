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

# Store dept as an addon pref so it stays between restarts
class Preferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	dept: bpy.props.IntProperty(name="Department", default=0)

# Keep this order intact, the dept is saved as an index
dept_items = [
	("modelling", "Modelling", ""),
	("surfacing", "Surfacing", ""),
	("rigging", "Rigging", ""),
	("assembly", "Assembly", ""),
	("layout", "Layout", ""),
	("animation", "Animation", ""),
	("fx", "FX", ""),
	("lighting", "Lighting", ""),
	("comp", "Comp", ""),
]

class Properties(bpy.types.PropertyGroup):
	def get_dept(self):
		return bpy.context.preferences.addons[__name__].preferences.dept

	def set_dept(self, value):
		bpy.context.preferences.addons[__name__].preferences.dept = value

	# Fetch properties
	fetch_asset: bpy.props.StringProperty(name="Asset Name")
	fetch_version: bpy.props.StringProperty(name="Version", default="latest")

	# Publish properties
	dept: bpy.props.EnumProperty(
		name="Department",
		items=dept_items,
		get=get_dept,
		set=set_dept
	)
	publish_asset: bpy.props.StringProperty(name="Asset Name")

class Publish_Operator(bpy.types.Operator):
	"""Save and increment the version of the above assets"""
	bl_idname = "pipeline.publish"
	bl_label = "Publish"

	def execute(self, context):
		props = context.scene.shitgrid_props

		# Directory for storing published Blender files for building
		blender_db = os.environ.get("SHITGRID_BLEND_DB")
		if not blender_db:
			self.report({"ERROR"}, "Missing environment variable SHITGRID_BLEND_DB!")
			return {"CANCELLED"}

		if not props.dept:
			self.report({"ERROR_INVALID_INPUT"}, "Please select a department!")
			return {"CANCELLED"}

		if not props.publish_asset:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in an asset!")
			return {"CANCELLED"}

		# Make sure to set the SHITGRID_BLEND_DB env var or this will break!
		asset_folder = os.path.join(blender_db, "wip", props.publish_asset)
		if not os.path.exists(asset_folder):
			self.report({"ERROR"}, "Asset {} doesn't exist yet!\nAdd it on the website.".format(props.publish_asset))
			return {"CANCELLED"}

		# Structure is "master/wip/asset/dept/asset_dept_v001.blend" for now
		dept_folder = os.path.join(asset_folder, props.dept)
		if not os.path.exists(dept_folder):
			os.mkdir(dept_folder)

		# Up version number based on file index in subfolder
		version = len([p for p in os.listdir(dept_folder) if os.path.isfile(os.path.join(dept_folder, p))]) + 1

		# Name is "asset_dept_v001.blend" for now
		file_name = "{}_{}_v{:03d}.blend".format(props.publish_asset, props.dept, version)

		# Save a copy. This copy should never be touched!
		bpy.ops.wm.save_as_mainfile(filepath=os.path.join(dept_folder, file_name), check_existing=True, copy=True)

		# Would be nice to add a popup box for this
		success_msg = "Published {} {} version {}!".format(props.publish_asset, props.dept, version)
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
		layout.prop(scn.shitgrid_props, "dept")
		layout.prop(scn.shitgrid_props, "publish_asset")
		layout.operator(Publish_Operator.bl_idname)

class Fetch_Operator(bpy.types.Operator):
	"""Fetch a published asset by combining parts together"""
	bl_idname = "pipeline.fetch"
	bl_label = "Fetch"

	def execute(self, context):
		props = context.scene.shitgrid_props

		if not props.fetch_asset:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in an asset!")
			return {"CANCELLED"}

		if not props.fetch_version:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in a version!")
			return {"CANCELLED"}

		# TODO
		return {"FINISHED"}

class Fetch_Panel(bpy.types.Panel):
	bl_label = "Fetch Asset"
	bl_idname = "ALA_PT_Shitgrid_Fetch"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		layout = self.layout
		scn = context.scene
		layout.prop(scn.shitgrid_props, "fetch_asset")
		layout.prop(scn.shitgrid_props, "fetch_version")
		layout.operator(Fetch_Operator.bl_idname)

# Dump all classes to register in here
classes = [Publish_Panel, Fetch_Panel, Publish_Operator, Fetch_Operator, Properties, Preferences]

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	scn = bpy.types.Scene
	scn.shitgrid_props = bpy.props.PointerProperty(type=Properties)

def unregister():
	scn = bpy.types.Scene
	del scn.shitgrid_props
	for cls in classes:
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()