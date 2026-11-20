"""Blender 4.3 add-on for exporting and restoring selected armature bones,
their Bone Collection memberships and their Bone Constraints."""

# Change this to "Anim Tools" or another tab name to move the panel.
PANEL_CATEGORY = "Rigging"

bl_info = {
    "name": "Yi Bone Collection Backup",
    "author": "OpenAI",
    "version": (1, 1, 0),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > configured tab",
    "description": "Export selected bones, Bone Collection memberships and Bone Constraints to JSON",
    "category": "Rigging",
}

import bpy
import json
import os
import mathutils


FILE_FORMAT = "blender_bone_collection_backup"
FILE_VERSION = 2
SUPPORTED_VERSIONS = {1, 2}

# Constraint properties that must not be written back.
_CONSTRAINT_SKIP_PROPS = {
    "rna_type",
    "type",
    "is_valid",
    "active",
    "is_override_data_editable",
    "error_location",
    "error_rotation",
}

# ID.id_type -> bpy.data collection name, used to resolve pointer targets.
_ID_COLLECTIONS = {
    "OBJECT": "objects",
    "ACTION": "actions",
    "TEXT": "texts",
    "CURVE": "curves",
    "MESH": "meshes",
    "ARMATURE": "armatures",
    "CAMERA": "cameras",
    "MOVIECLIP": "movieclips",
    "CACHEFILE": "cache_files",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Constraint serialization (generic, RNA based)
# ---------------------------------------------------------------------------

def _serialize_value(value, owner_obj):
    """Convert an RNA value into something JSON can store."""
    if value is None:
        return None
    if isinstance(value, bpy.types.ID):
        # "self" lets a constraint that targets its own armature be remapped
        # to the destination armature on import (e.g. copying between rigs).
        return {"__id__": value.id_type, "name": value.name, "self": value == owner_obj}
    if isinstance(value, mathutils.Matrix):
        return {"__matrix__": [list(row) for row in value]}
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, set):
        return {"__set__": sorted(value)}
    try:
        return list(value)
    except TypeError:
        return None


def _serialize_struct(struct, owner_obj):
    """Store every writable property of a constraint (or constraint target)."""
    data = {}
    for prop in struct.bl_rna.properties:
        pid = prop.identifier
        if pid in _CONSTRAINT_SKIP_PROPS:
            continue
        if prop.type == "COLLECTION":
            items = getattr(struct, pid)
            data[pid] = {"__collection__": [_serialize_struct(item, owner_obj) for item in items]}
            continue
        if prop.is_readonly:
            continue
        value = getattr(struct, pid)
        if prop.type == "POINTER" and value is not None and not isinstance(value, bpy.types.ID):
            continue
        data[pid] = _serialize_value(value, owner_obj)
    return data


def _serialize_constraints(pose_bone, owner_obj):
    return [
        {"type": con.type, "props": _serialize_struct(con, owner_obj)}
        for con in pose_bone.constraints
    ]


def _resolve_value(value, owner_obj, missing):
    """Convert a stored JSON value back into an RNA value."""
    if isinstance(value, dict):
        if "__id__" in value:
            if value.get("self"):
                return owner_obj
            coll_name = _ID_COLLECTIONS.get(value["__id__"])
            coll = getattr(bpy.data, coll_name, None) if coll_name else None
            found = coll.get(value["name"]) if coll is not None else None
            if found is None:
                missing.add(value["name"])
            return found
        if "__matrix__" in value:
            return mathutils.Matrix(value["__matrix__"])
        if "__set__" in value:
            return set(value["__set__"])
    return value


def _apply_phase(key, value):
    # Pointers first, then subtarget strings, then everything else,
    # so bone names / spaces are validated against an existing target.
    if value is None or (isinstance(value, dict) and "__id__" in value):
        return 0
    if "subtarget" in key:
        return 1
    return 2


def _apply_struct(struct, data, owner_obj, missing, warnings):
    plain = [
        (key, value) for key, value in data.items()
        if not (isinstance(value, dict) and "__collection__" in value)
    ]
    for key, value in sorted(plain, key=lambda kv: _apply_phase(*kv)):
        if key not in struct.bl_rna.properties:
            continue
        try:
            setattr(struct, key, _resolve_value(value, owner_obj, missing))
        except (AttributeError, TypeError, ValueError) as exc:
            warnings.append("{}.{}: {}".format(struct.name if hasattr(struct, "name") else struct, key, exc))

    # Collections such as the Armature constraint's "targets".
    for key, value in data.items():
        if not (isinstance(value, dict) and "__collection__" in value):
            continue
        coll = getattr(struct, key, None)
        if coll is None or not hasattr(coll, "new"):
            continue
        for item in list(coll):
            if hasattr(coll, "remove"):
                coll.remove(item)
        for item_data in value["__collection__"]:
            new_item = coll.new()
            _apply_struct(new_item, item_data, owner_obj, missing, warnings)


def _restore_constraints(pose_bone, constraint_records, owner_obj, missing, warnings):
    for con in list(pose_bone.constraints):
        pose_bone.constraints.remove(con)
    count = 0
    for record in constraint_records:
        try:
            con = pose_bone.constraints.new(record["type"])
        except (TypeError, ValueError, KeyError) as exc:
            warnings.append("{}: cannot create constraint ({})".format(pose_bone.name, exc))
            continue
        _apply_struct(con, record.get("props", {}), owner_obj, missing, warnings)
        count += 1
    return count


# ---------------------------------------------------------------------------
# Export / Import
# ---------------------------------------------------------------------------

def export_bones(filepath, armature=None, bones=None, include_constraints=True, verbose=True):
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
    constraint_total = 0
    for name in selected_names:
        bone = arm_data.bones.get(name)
        if bone is None:
            if verbose:
                print("[skip] Bone not found: {}".format(name))
            continue
        memberships = sorted(collection.name for collection in bone.collections)
        collection_names.update(memberships)
        record = {
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
        }
        if include_constraints:
            pose_bone = obj.pose.bones.get(name)
            constraints = _serialize_constraints(pose_bone, obj) if pose_bone else []
            record["constraints"] = constraints
            constraint_total += len(constraints)
        records.append(record)

    if not records:
        raise ValueError("No valid bones were found to export.")

    payload = {
        "format": FILE_FORMAT,
        "version": FILE_VERSION,
        "source_armature": obj.name,
        "include_constraints": bool(include_constraints),
        "bones": records,
        "collections": sorted(collection_names),
    }
    with open(filepath, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    if verbose:
        print("[ok] Exported {} bone(s), {} constraint(s) to {}".format(
            len(records), constraint_total, filepath))
    return {"bones": len(records), "constraints": constraint_total}


def import_bones(filepath, armature=None, conflict_mode="ADD_ONLY",
                 include_constraints=True, verbose=True):
    """Restore bones from JSON. conflict_mode is ADD_ONLY or OVERWRITE."""
    obj = _get_armature_object(armature)
    with open(filepath, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if payload.get("format") != FILE_FORMAT:
        raise ValueError("This is not a supported bone backup JSON file.")
    if payload.get("version") not in SUPPORTED_VERSIONS:
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
    constraint_count = 0
    missing_targets = set()
    warnings = []

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

        # Constraints live on pose bones, so restore them in Object mode
        # after every bone exists (targets may point to other imported bones).
        bpy.ops.object.mode_set(mode="OBJECT")
        if include_constraints:
            for name, record in record_by_name.items():
                if name in skipped_names or "constraints" not in record:
                    continue
                pose_bone = obj.pose.bones.get(name)
                if pose_bone is None:
                    continue
                constraint_count += _restore_constraints(
                    pose_bone, record["constraints"], obj, missing_targets, warnings)

    finally:
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        if was_selected is not None and was_selected.name in bpy.context.view_layer.objects:
            bpy.context.view_layer.objects.active = was_selected

    if verbose:
        print("[ok] Created: {}".format(", ".join(created_names) or "none"))
        print("[info] Updated: {}".format(", ".join(updated_names) or "none"))
        print("[skip] Existing bones kept: {}".format(", ".join(skipped_names) or "none"))
        print("[ok] Constraints restored: {}".format(constraint_count))
        if missing_targets:
            print("[warn] Missing constraint targets: {}".format(", ".join(sorted(missing_targets))))
        for line in warnings:
            print("[warn] {}".format(line))
    return {
        "created": created_names,
        "updated": updated_names,
        "skipped": skipped_names,
        "constraints": constraint_count,
        "missing_targets": sorted(missing_targets),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Operators / UI
# ---------------------------------------------------------------------------

class ARMATURE_OT_export_bone_backup(bpy.types.Operator):
    bl_idname = "armature.export_bone_backup"
    bl_label = "Export Selected Bones"
    bl_options = {"REGISTER"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})
    include_constraints: bpy.props.BoolProperty(
        name="Include Bone Constraints",
        description="Also export the pose bone constraints of the selected bones",
        default=True,
        options={"HIDDEN"},
    )

    def execute(self, context):
        try:
            result = export_bones(self.filepath, include_constraints=self.include_constraints)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "Exported {} bone(s), {} constraint(s).".format(
            result["bones"], result["constraints"]))
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
            ("ADD_ONLY", "Add Missing Only", "Keep existing bones (and their constraints) unchanged"),
            ("OVERWRITE", "Overwrite Existing", "Update matching bones and replace their constraints"),
        ],
        default="ADD_ONLY",
    )
    include_constraints: bpy.props.BoolProperty(
        name="Include Bone Constraints",
        description="Restore pose bone constraints stored in the file",
        default=True,
        options={"HIDDEN"},
    )

    def execute(self, context):
        try:
            result = import_bones(
                self.filepath,
                conflict_mode=self.conflict_mode,
                include_constraints=self.include_constraints,
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        message = "Restored {} new bone(s), {} constraint(s).".format(
            len(result["created"]), result["constraints"])
        if result["missing_targets"] or result["warnings"]:
            message += " Some targets missing, see System Console."
            self.report({"WARNING"}, message)
        else:
            self.report({"INFO"}, message)
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
        layout.label(text="Select bones (Edit/Pose) to export")
        layout.label(text="collections, relationships & constraints")

        # Keep the option visible in the sidebar instead of hiding it in the
        # file browser's operator options. Both buttons use this shared setting.
        layout.prop(
            context.scene,
            "bone_backup_include_constraints",
            text="Include Bone Constraints",
        )

        export_op = layout.operator("armature.export_bone_backup", icon="EXPORT")
        export_op.include_constraints = context.scene.bone_backup_include_constraints
        import_op = layout.operator("armature.import_bone_backup", icon="IMPORT")
        import_op.include_constraints = context.scene.bone_backup_include_constraints
        layout.label(text="Exported file is .json format")


_CLASSES = (
    ARMATURE_OT_export_bone_backup,
    ARMATURE_OT_import_bone_backup,
    VIEW3D_PT_bone_collection_backup,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bone_backup_include_constraints = bpy.props.BoolProperty(
        name="Include Bone Constraints",
        description="Include pose bone constraints when exporting or importing bones",
        default=True,
    )


def unregister():
    if hasattr(bpy.types.Scene, "bone_backup_include_constraints"):
        del bpy.types.Scene.bone_backup_include_constraints
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
