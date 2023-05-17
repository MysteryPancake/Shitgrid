"""
Wipes the current file for a clean asset build
This has to be run separately because it makes Blender forget where it is
"""
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)