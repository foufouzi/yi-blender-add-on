"""Save and restore Rigify pose-bone custom shapes in Blender 4.3.

Run this file from Blender's Text Editor. The Rigify Custom Shapes panel is
available in the 3D Viewport sidebar under the Rigify tab. Presets are saved
as external JSON files; referenced custom-shape objects must remain in scene.
"""

import bpy
import json
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper


def _get_rig(obj):
    """Return an armature object or None."""
    if obj and obj.type == "ARMATURE":
        return obj
    return None


def _build_custom_shape_data(rig):
    """Build a JSON-compatible snapshot from an armature object."""
    records = []
    for bone in rig.pose.bones:
        if not bone.custom_shape:
            continue

        transform = bone.custom_shape_transform
        records.append({
            "bone": bone.name,
            "shape": bone.custom_shape.name,
            "transform_bone": transform.name if transform else None,
            "translation": list(bone.custom_shape_translation),
            "rotation": list(bone.custom_shape_rotation_euler),
            "scale_xyz": list(bone.custom_shape_scale_xyz),
            "use_bone_size": bool(bone.use_custom_shape_bone_size),
            "wire_width": float(bone.custom_shape_wire_width),
        })

    return {
        "version": 1,
        "source_rig": rig.name,
        "bones": records,
    }


def save_custom_shapes(rig=None, filepath=None, verbose=True):
    """Save custom-shape assignments and display settings to an external JSON.

    Args:
        rig: Armature object; defaults to the active object.
        filepath: Destination JSON file path. Required.
        verbose: Print a concise report to the system console.

    Returns:
        Number of pose bones saved, or 0 if saving could not be completed.
    """
    rig = _get_rig(rig or bpy.context.view_layer.objects.active)
    if rig is None:
        if verbose:
            print("[fail] Select an armature object before saving.")
        return 0
    if not filepath:
        if verbose:
            print("[fail] Choose a JSON file path before saving.")
        return 0

    payload = _build_custom_shape_data(rig)
    try:
        with open(bpy.path.abspath(filepath), "w", encoding="utf-8") as json_file:
            json.dump(payload, json_file, indent=2, ensure_ascii=True)
    except (OSError, TypeError, ValueError) as exc:
        if verbose:
            print("[fail] Could not save JSON: {0}".format(exc))
        return 0

    count = len(payload["bones"])
    if verbose:
        print("[ok] Saved custom shapes for {0} bones to '{1}'.".format(
            count, filepath
        ))
    return count


def _load_custom_shape_data(filepath):
    """Load and validate a custom-shape JSON file."""
    with open(bpy.path.abspath(filepath), "r", encoding="utf-8") as json_file:
        payload = json.load(json_file)
    if not isinstance(payload, dict) or not isinstance(payload.get("bones"), list):
        raise ValueError("JSON does not contain a valid bones list.")
    return payload


def apply_custom_shapes(rig=None, filepath=None, verbose=True):
    """Apply external JSON custom-shape data to an armature by bone name.

    Custom shape objects must still exist in the scene. Missing bones, shapes,
    or transform bones are skipped and reported.

    Args:
        rig: Destination armature; defaults to the active object.
        filepath: Source JSON file path. Required.
        verbose: Print a concise report to the system console.

    Returns:
        Number of pose bones restored, or 0 if no data/armature is available.
    """
    rig = _get_rig(rig or bpy.context.view_layer.objects.active)
    if rig is None:
        if verbose:
            print("[fail] Select the generated armature before applying.")
        return 0
    if not filepath:
        if verbose:
            print("[fail] Choose a JSON file path before applying.")
        return 0

    try:
        payload = _load_custom_shape_data(filepath)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        if verbose:
            print("[fail] Could not read custom-shape JSON: {0}".format(exc))
        return 0

    restored = 0
    skipped = []
    for record in payload.get("bones", []):
        if not isinstance(record, dict):
            skipped.append("invalid bone record")
            continue

        bone_name = record.get("bone", "")
        shape_name = record.get("shape", "")
        bone = rig.pose.bones.get(bone_name)
        shape = bpy.data.objects.get(shape_name)
        transform_name = record.get("transform_bone")
        transform = rig.pose.bones.get(transform_name) if transform_name else None

        if bone is None:
            skipped.append("missing bone: {0}".format(bone_name))
            continue
        if shape is None:
            skipped.append("missing shape object: {0}".format(shape_name))
            continue
        if transform_name and transform is None:
            skipped.append("missing transform bone: {0}".format(transform_name))
            continue

        try:
            bone.custom_shape = shape
            bone.custom_shape_transform = transform
            bone.custom_shape_translation = record.get("translation", (0.0, 0.0, 0.0))
            bone.custom_shape_rotation_euler = record.get("rotation", (0.0, 0.0, 0.0))
            bone.custom_shape_scale_xyz = record.get("scale_xyz", (1.0, 1.0, 1.0))
            bone.use_custom_shape_bone_size = record.get("use_bone_size", False)
            bone.custom_shape_wire_width = record.get("wire_width", 1.0)
        except (TypeError, ValueError, AttributeError) as exc:
            skipped.append("invalid settings for {0}: {1}".format(bone_name, exc))
            continue
        restored += 1

    if verbose:
        print("[ok] Restored custom shapes on {0} bones for '{1}'.".format(
            restored, rig.name
        ))
        for message in skipped:
            print("[skip] {0}".format(message))
    return restored


class RIGIFYCUSTOMSHAPES_OT_save(bpy.types.Operator, ExportHelper):
    bl_idname = "rigify_custom_shapes.save"
    bl_label = "Save Custom Shapes to JSON"
    bl_description = "Export custom shapes and display settings from the active armature"
    bl_options = {'REGISTER'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return bool(context.active_object and context.active_object.type == "ARMATURE")

    def execute(self, context):
        count = save_custom_shapes(context.active_object, self.filepath)
        if count == 0:
            self.report({'WARNING'}, "No custom shapes were saved. Check the system console.")
        else:
            self.report({'INFO'}, "Saved custom shapes for {0} bones.".format(count))
        return {'FINISHED'}


class RIGIFYCUSTOMSHAPES_OT_apply(bpy.types.Operator, ImportHelper):
    bl_idname = "rigify_custom_shapes.apply"
    bl_label = "Apply JSON to Active Rig"
    bl_description = "Restore custom shapes from a JSON file onto the active armature"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return bool(context.active_object and context.active_object.type == "ARMATURE")

    def execute(self, context):
        count = apply_custom_shapes(context.active_object, self.filepath)
        if count == 0:
            self.report({'WARNING'}, "No custom shapes were restored. Check the system console.")
        else:
            self.report({'INFO'}, "Restored custom shapes on {0} bones.".format(count))
        return {'FINISHED'}


class RIGIFYCUSTOMSHAPES_PT_panel(bpy.types.Panel):
    bl_label = "Rigify Custom Shapes"
    bl_idname = "RIGIFYCUSTOMSHAPES_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Rigify"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Export from the customized rig:")
        layout.operator("rigify_custom_shapes.save", icon="FILE_TICK")
        layout.separator()
        layout.label(text="After Generate Rig, select the new rig:")
        layout.operator("rigify_custom_shapes.apply", icon="POSE_HLT")
        layout.label(text="Settings are saved in an external JSON file.", icon="INFO")


_CLASSES = (
    RIGIFYCUSTOMSHAPES_OT_save,
    RIGIFYCUSTOMSHAPES_OT_apply,
    RIGIFYCUSTOMSHAPES_PT_panel,
)


def register():
    """Register the panel and operators in Blender."""
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister the panel and operators from Blender."""
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    try:
        unregister()
    except (RuntimeError, ValueError):
        pass
    register()
    print("[ok] Rigify Custom Shapes panel registered in the 3D Viewport sidebar.")
