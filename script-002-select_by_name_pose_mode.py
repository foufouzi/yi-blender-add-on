import bpy

# Deselect all first (optional)
bpy.ops.pose.select_all(action='DESELECT')

# Select bones containing "xxx"
armature = bpy.context.active_object
for bone in armature.pose.bones:
    if "ik" in bone.name:
        bone.bone.select = True
