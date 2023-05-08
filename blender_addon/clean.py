# Completely clean the Blender file before building, no default cubes allowed
# This has to be run separately because Blender forgets the context
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)