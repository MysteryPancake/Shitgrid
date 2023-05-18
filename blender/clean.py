"""
Wipes the current Blender file for a clean asset build.\n
This has to be run separately because it makes Blender forget where it is.
"""
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)