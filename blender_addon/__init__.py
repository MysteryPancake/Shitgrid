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

# Store department as an addon preference so it keeps between restarts
class Preferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	department: bpy.props.IntProperty(name="Department", default=0)

# Keep this order intact, the department is saved as an index
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

	def get_department(self):
		return bpy.context.preferences.addons[__name__].preferences.department

	def set_department(self, value):
		# Save selected department to addon preferences so it stays between sessions
		bpy.context.preferences.addons[__name__].preferences.department = value

	department: bpy.props.EnumProperty(
		name="Department",
		items=dept_items,
		get=get_department,
		set=set_department
	)
	task: bpy.props.StringProperty(name="Task")

# Publish button
class Publish_Operator(bpy.types.Operator):
	"""Save and increment the version of the above assets"""
	bl_idname = "pipeline.publish"
	bl_label = "Publish"

	def execute(self, context):
		props = context.scene.shitgrid_props

		if not props.department:
			self.report({"ERROR_INVALID_INPUT"}, "Please select a department!")
			return {"CANCELLED"}

		if not props.task:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in a task!")
			return {"CANCELLED"}

		# Make sure to set the SHITGRID_BLEND_DB environment variable or this will break!
		blender_db = os.environ["SHITGRID_BLEND_DB"]
		task_folder = os.path.join(blender_db, props.task)
		if not os.path.exists(task_folder):
			self.report({"ERROR"}, "Task {} doesn't exist yet!\nAdd it on the website.".format(props.task))
			return {"CANCELLED"}

		# Structure is "wip/task/dept/task_dept_v001.blend" for now
		dept_folder = os.path.join(task_folder, props.department)
		if not os.path.exists(dept_folder):
			os.mkdir(dept_folder)

		# Up version number based on file index in subfolder
		version = len([p for p in os.listdir(dept_folder) if os.path.isfile(os.path.join(dept_folder, p))]) + 1

		# Name is "task_dept_v001.blend" for now
		file_name = "{}_{}_v{:03d}.blend".format(props.task, props.department, version)

		# Save a copy. This copy should never be touched!
		bpy.ops.wm.save_as_mainfile(filepath=os.path.join(dept_folder, file_name), check_existing=True, copy=True)

		# Would be nice to add a popup box for this
		success_msg = "Published {} {} version {}!".format(props.task, props.department, version)
		self.report({"INFO"}, success_msg)

		return {"FINISHED"}

# Add pipeline to side menu (activated with N)
class Publish_Panel(bpy.types.Panel):
	bl_label = "Publish"
	bl_idname = "ALA_PT_Shitgrid"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Shitgrid"

	def draw(self, context):
		layout = self.layout
		scn = context.scene

		layout.prop(scn.shitgrid_props, "department")
		layout.prop(scn.shitgrid_props, "task")
		layout.operator(Publish_Operator.bl_idname)

# Dump all classes Blender has to register in here
classes = [Publish_Panel, Properties, Preferences, Publish_Operator]

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