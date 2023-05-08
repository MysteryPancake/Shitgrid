# Completely clean the Blender file before building, no default cubes allowed
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)