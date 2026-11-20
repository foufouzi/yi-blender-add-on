"""Blender 4.3 add-on for exporting and restoring selected armature bones."""

# Change this to "Anim Tools" or another tab name to move the panel.
PANEL_CATEGORY = "Rigging"

bl_info = {
    "name": "Yi Bone Collection Backup",
    "author": "OpenAI",
    "version": (1, 0, 0),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > configured tab",
    "description": "Export selected bones and Bone Collection memberships to JSON",
    "category": "Rigging",
}

import bpy
import json
import os


def _get_armature_object(armature=None):
    obj = armature or bpy.context.object
    if obj is None or obj.type != "ARMATURE":
        raise ValueError("Select or activate an armature object.")
    return obj


def _selected_bone_names(obj):
    if obj.mode == "EDIT":
        return [bone.name for bone in obj.data.edit_bones if bone.select]
    if obj.mode == "POSE":
        pose_bones = bpy.context.selected_pose_bones or []
        return [bone.name for bone in pose_bones if bone.id_data == obj]
    return []


def export_bones(filepath, armature=None, bones=None, verbose=True):
    """Export selected bones or the explicitly supplied bone names to JSON."""
    obj = _get_armature_object(armature)
    selected_names = list(bones) if bones is not None else _selected_bone_names(obj)
    if obj.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    if not selected_names:
        raise ValueError("No bones selected. Select bones in Edit or Pose mode first.")

    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = obj.data.edit_bones
    roll_by_name = {
        name: float(edit_bones[name].roll)
        for name in selected_names
        if edit_bones.get(name) is not None
    }
    bpy.ops.object.mode_set(mode="OBJECT")

    arm_data = obj.data
    records = []
    collection_names = set()
    for name in selected_names:
        bone = arm_data.bones.get(name)
        if bone is None:
            if verbose:
                print("[skip] Bone not found: {}".format(name))
            continue
        memberships = sorted(collection.name for collection in bone.collections)
        collection_names.update(memberships)
        records.append({
            "name": bone.name,
            "head": list(bone.head_local),
            "tail": list(bone.tail_local),
            "roll": roll_by_name.get(name, 0.0),
            "parent": bone.parent.name if bone.parent else None,
            "use_connect": bool(bone.use_connect),
            "use_deform": bool(bone.use_deform),
            "inherit_scale": bone.inherit_scale,
            "inherit_rotation": bool(bone.use_inherit_rotation),
            "collections": memberships,
        })

    if not records:
        raise ValueError("No valid bones were found to export.")

    payload = {
        "format": "blender_bone_collection_backup",
        "version": 1,
        "source_armature": obj.name,
        "bones": records,
        "collections": sorted(collection_names),
    }
    with open(filepath, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    if verbose:
        print("[ok] Exported {} bone(s) to {}".format(len(records), filepath))
    return len(records)


def import_bones(filepath, armature=None, conflict_mode="ADD_ONLY", verbose=True):
    """Restore bones from JSON. conflict_mode is ADD_ONLY or OVERWRITE."""
    obj = _get_armature_object(armature)
    with open(filepath, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if payload.get("format") != "blender_bone_collection_backup":
        raise ValueError("This is not a supported bone backup JSON file.")
    if payload.get("version") != 1:
        raise ValueError("Unsupported bone backup version.")
    records = payload.get("bones")
    if not isinstance(records, list) or not records:
        raise ValueError("The backup file contains no bones.")
    if conflict_mode not in {"ADD_ONLY", "OVERWRITE"}:
        raise ValueError("Choose ADD_ONLY or OVERWRITE for same-name bones.")

    was_selected = bpy.context.view_layer.objects.active
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    edit_bones = obj.data.edit_bones
    record_by_name = {record["name"]: record for record in records}
    processed = {}
    created_names = []
    updated_names = []
    skipped_names = []

    try:
        for record in records:
            name = record["name"]
            existing = edit_bones.get(name)
            if existing is not None and conflict_mode == "ADD_ONLY":
                processed[name] = existing
                skipped_names.append(name)
                continue
            bone = existing or edit_bones.new(name)
            bone.head = record["head"]
            bone.tail = record["tail"]
            bone.roll = record.get("roll", 0.0)
            bone.use_connect = False
            bone.use_deform = record.get("use_deform", True)
            bone.inherit_scale = record.get("inherit_scale", "FULL")
            bone.use_inherit_rotation = record.get("inherit_rotation", True)
            processed[name] = bone
            if existing is None:
                created_names.append(name)
            else:
                updated_names.append(name)

        for name, bone in processed.items():
            if name in skipped_names:
                continue
            parent_name = record_by_name[name].get("parent")
            parent = edit_bones.get(parent_name) if parent_name else None
            if parent is not None and parent != bone:
                bone.parent = parent
                bone.use_connect = bool(record_by_name[name].get("use_connect", False))
            else:
                bone.parent = None
                bone.use_connect = False

        bpy.ops.object.mode_set(mode="OBJECT")

        arm_data = obj.data
        for collection_name in payload.get("collections", []):
            if arm_data.collections.get(collection_name) is None:
                arm_data.collections.new(collection_name)

        bpy.ops.object.mode_set(mode="EDIT")
        edit_bones = obj.data.edit_bones
        for name, record in record_by_name.items():
            if name in skipped_names:
                continue
            edit_bone = edit_bones.get(name)
            if edit_bone is None:
                continue
            for collection in list(arm_data.collections):
                collection.unassign(edit_bone)
            for collection_name in record.get("collections", []):
                collection = arm_data.collections.get(collection_name)
                if collection is not None:
                    collection.assign(edit_bone)

    finally:
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        if was_selected is not None and was_selected.name in bpy.context.view_layer.objects:
            bpy.context.view_layer.objects.active = was_selected

    if verbose:
        print("[ok] Created: {}".format(", ".join(created_names) or "none"))
        print("[info] Updated: {}".format(", ".join(updated_names) or "none"))
        print("[skip] Existing bones kept: {}".format(", ".join(skipped_names) or "none"))
    return {"created": created_names, "updated": updated_names, "skipped": skipped_names}


class ARMATURE_OT_export_bone_backup(bpy.types.Operator):
    bl_idname = "armature.export_bone_backup"
    bl_label = "Export Selected Bones"
    bl_options = {"REGISTER"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        try:
            export_bones(self.filepath)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "Bone backup exported.")
        return {"FINISHED"}

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = os.path.join(os.path.expanduser("~"), "bone_backup.json")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ARMATURE_OT_import_bone_backup(bpy.types.Operator):
    bl_idname = "armature.import_bone_backup"
    bl_label = "Import Bone Backup"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})
    conflict_mode: bpy.props.EnumProperty(
        name="Same-name bones",
        description="Choose what to do when a bone already exists",
        items=[
            ("ADD_ONLY", "Add Missing Only", "Keep existing bones unchanged"),
            ("OVERWRITE", "Overwrite Existing", "Update matching bones from the file"),
        ],
        default="ADD_ONLY",
    )

    def execute(self, context):
        try:
            result = import_bones(self.filepath, conflict_mode=self.conflict_mode)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        summary = len(result["created"])
        self.report({"INFO"}, "Restored {} new bone(s).".format(summary))
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class VIEW3D_PT_bone_collection_backup(bpy.types.Panel):
    bl_label = "Yi Bone Backup Tool"
    bl_idname = "VIEW3D_PT_bone_collection_backup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = PANEL_CATEGORY

    def draw_header(self, context):
        self.layout.label(text="", icon="SOLO_ON")

    def draw(self, context):
        layout = self.layout
        layout.label(text="Selected bones in Edit mode to export collection & relationships")
        layout.operator("armature.export_bone_backup", icon="EXPORT")
        layout.operator("armature.import_bone_backup", icon="IMPORT")
        layout.label(text="Exported file is .json format")


_CLASSES = (
    ARMATURE_OT_export_bone_backup,
    ARMATURE_OT_import_bone_backup,
    VIEW3D_PT_bone_collection_backup,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
