import bpy

PARENT_BONE_NAME = "Ro"

armature = bpy.context.object

if armature is None or armature.type != "ARMATURE":
    raise RuntimeError("Please make the armature the active object.")

if armature.mode != "EDIT":
    raise RuntimeError("Please switch the armature to Edit Mode first.")

parent_bone = armature.data.edit_bones.get(PARENT_BONE_NAME)

if parent_bone is None:
    raise ValueError(f"Parent bone not found: {PARENT_BONE_NAME}")

selected_bones = [
    bone for bone in armature.data.edit_bones
    if bone.select
]

if not selected_bones:
    raise RuntimeError("No bones are selected.")

if parent_bone in selected_bones:
    selected_bones.remove(parent_bone)

for bone in selected_bones:
    if bone == parent_bone:
        continue

    # Prevent parenting the parent bone to itself.
    # Keep the bone's current position and orientation.
    bone.parent = parent_bone
    bone.use_connect = False

print(
    f"Parented {len(selected_bones)} bone(s) "
    f"to '{PARENT_BONE_NAME}'."
)
