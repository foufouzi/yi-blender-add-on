import bpy

arm = bpy.context.object

if arm and arm.type == "ARMATURE" and arm.mode == "EDIT":
    for bone in arm.data.edit_bones:
        if bone.select:
            bone.use_deform = False
else:
    print("Select an Armature and enter Edit Mode before running this script.")