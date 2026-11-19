bl_info = {
    "name": "Yi_only_key_unlocked_channel",
    "author": "webby",
    "version": (1, 0, 0),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar (N) > Anim Tools",
    "description": "Isolate selected controllers and key only unlocked channels",
    "category": "Animation",
}

import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty


INTERP_ITEMS = [
    ('KEEP', "Preference Default", "Use the interpolation set in Preferences > Animation"),
    ('CONSTANT', "Constant (Stepped)", "Stepped keys, good for blocking"),
    ('LINEAR', "Linear", "Linear interpolation"),
    ('BEZIER', "Bezier", "Smooth interpolation, good for spline pass"),
]


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------

class ACT_Settings(bpy.types.PropertyGroup):
    include_custom_props: BoolProperty(
        name="Include Custom Properties",
        description="Also key numeric custom properties on the controllers",
        default=False,
    )
    interpolation: EnumProperty(
        name="Interpolation",
        description="Interpolation applied to the new keys",
        items=INTERP_ITEMS,
        default='KEEP',
    )


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _get_targets(context):
    """Return list of (owner_object, target, group_name, is_pose_bone)."""
    targets = []
    if context.mode == 'POSE':
        for pb in context.selected_pose_bones or []:
            targets.append((pb.id_data, pb, pb.name, True))
    elif context.mode == 'OBJECT':
        for obj in context.selected_objects:
            targets.append((obj, obj, "Object Transforms", False))
    return targets


def _full_path(target, prop, is_pose_bone):
    """Build the F-Curve data path relative to the owner object."""
    if not is_pose_bone:
        return prop
    prefix = target.path_from_id()  # e.g. pose.bones["CTRL_hand.L"]
    return prefix + prop if prop.startswith("[") else prefix + "." + prop


def _insert(owner, target, prop, index, frame, group, is_pose_bone, keyed):
    try:
        ok = target.keyframe_insert(prop, index=index, frame=frame, group=group)
    except (TypeError, RuntimeError):
        return 0
    if not ok:
        return 0
    keyed.append((owner, _full_path(target, prop, is_pose_bone), index))
    if index >= 0:
        return 1
    value = target.path_resolve(prop)
    try:
        return len(value)
    except TypeError:
        return 1


def _key_unlocked(owner, target, frame, group, is_pose_bone, include_custom, keyed):
    n = 0
    args = (frame, group, is_pose_bone, keyed)

    # Location
    for i, locked in enumerate(target.lock_location):
        if not locked:
            n += _insert(owner, target, "location", i, *args)

    # Rotation
    mode = target.rotation_mode
    if mode == 'QUATERNION':
        if target.lock_rotations_4d:
            if not target.lock_rotation_w:
                n += _insert(owner, target, "rotation_quaternion", 0, *args)
            for i, locked in enumerate(target.lock_rotation):
                if not locked:
                    n += _insert(owner, target, "rotation_quaternion", i + 1, *args)
        elif not all(target.lock_rotation):
            n += _insert(owner, target, "rotation_quaternion", -1, *args)
    elif mode == 'AXIS_ANGLE':
        if not all(target.lock_rotation):
            n += _insert(owner, target, "rotation_axis_angle", -1, *args)
    else:  # Euler
        for i, locked in enumerate(target.lock_rotation):
            if not locked:
                n += _insert(owner, target, "rotation_euler", i, *args)

    # Scale
    for i, locked in enumerate(target.lock_scale):
        if not locked:
            n += _insert(owner, target, "scale", i, *args)

    # Custom properties
    if include_custom:
        for key in target.keys():
            if key.startswith("_"):
                continue
            if isinstance(target[key], (int, float)):
                n += _insert(owner, target, f'["{key}"]', -1, *args)

    return n


def _apply_interpolation(keyed, frame, interp):
    if interp == 'KEEP':
        return
    for owner, path, index in keyed:
        ad = owner.animation_data
        if not ad or not ad.action:
            continue
        for fc in ad.action.fcurves:
            if fc.data_path != path:
                continue
            if index >= 0 and fc.array_index != index:
                continue
            for kp in fc.keyframe_points:
                if abs(kp.co.x - frame) < 0.001:
                    kp.interpolation = interp
            fc.update()


# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------

class ACT_OT_toggle_isolate(bpy.types.Operator):
    """Toggle: show only selected controllers / reveal all"""
    bl_idname = "anim_tools.toggle_isolate"
    bl_label = "Isolate Selected"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode in {'POSE', 'OBJECT'}

    def execute(self, context):
        if context.mode == 'POSE':
            arm = context.active_object.data
            if any(b.hide for b in arm.bones):
                bpy.ops.pose.reveal(select=False)
                self.report({'INFO'}, "Revealed all bones")
            else:
                bpy.ops.pose.hide(unselected=True)
                self.report({'INFO'}, "Isolated selected bones")
        else:
            if any(o.hide_get() for o in context.view_layer.objects):
                bpy.ops.object.hide_view_clear(select=False)
                self.report({'INFO'}, "Revealed all objects")
            else:
                bpy.ops.object.hide_view_set(unselected=True)
                self.report({'INFO'}, "Isolated selected objects")
        return {'FINISHED'}


class ACT_OT_key_unlocked(bpy.types.Operator):
    """Insert keyframes on all unlocked channels of the selected controllers"""
    bl_idname = "anim_tools.key_unlocked"
    bl_label = "Key Unlocked Channels"
    bl_options = {'REGISTER', 'UNDO'}

    include_custom_props: BoolProperty(name="Include Custom Properties", default=False)
    interpolation: EnumProperty(name="Interpolation", items=INTERP_ITEMS, default='KEEP')

    @classmethod
    def poll(cls, context):
        if context.mode == 'POSE':
            return bool(context.selected_pose_bones)
        if context.mode == 'OBJECT':
            return bool(context.selected_objects)
        return False

    def invoke(self, context, event):
        # Pull defaults from the panel settings when called from a hotkey
        s = context.scene.anim_ctrl_tools
        if not self.properties.is_property_set("include_custom_props"):
            self.include_custom_props = s.include_custom_props
        if not self.properties.is_property_set("interpolation"):
            self.interpolation = s.interpolation
        return self.execute(context)

    def execute(self, context):
        frame = context.scene.frame_current
        keyed = []
        count = 0
        for owner, target, group, is_pb in _get_targets(context):
            count += _key_unlocked(owner, target, frame, group, is_pb,
                                   self.include_custom_props, keyed)

        _apply_interpolation(keyed, frame, self.interpolation)

        for area in context.screen.areas:
            area.tag_redraw()

        self.report({'INFO'}, f"Keyed {count} channels on frame {frame}")
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# Panel
# -----------------------------------------------------------------------------

class ACT_PT_main(bpy.types.Panel):
    bl_label = "Yi_Only Key Unlocked Channel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Anim Tools"
    
    def draw_header(self, context):
        self.layout.label(text="", icon='SOLO_ON')

    def draw(self, context):
        layout = self.layout
        s = context.scene.anim_ctrl_tools

        box = layout.box()
        box.label(text="Visibility", icon='HIDE_OFF')
        box.operator(ACT_OT_toggle_isolate.bl_idname, icon='RESTRICT_SELECT_OFF')

        box = layout.box()
        box.label(text="Keyframe", icon='KEYFRAME_HLT')
        box.prop(s, "include_custom_props")
        box.prop(s, "interpolation", text="")
        op = box.operator(ACT_OT_key_unlocked.bl_idname, icon='KEY_HLT')
        op.include_custom_props = s.include_custom_props
        op.interpolation = s.interpolation

        col = layout.column(align=True)
        col.scale_y = 0.8
        col.label(text="Ctrl+Alt+H : Isolate toggle")
        col.label(text="Shift+K : Key unlocked")


# -----------------------------------------------------------------------------
# Register
# -----------------------------------------------------------------------------

classes = (
    ACT_Settings,
    ACT_OT_toggle_isolate,
    ACT_OT_key_unlocked,
    ACT_PT_main,
)

addon_keymaps = []


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.anim_ctrl_tools = PointerProperty(type=ACT_Settings)

    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(ACT_OT_toggle_isolate.bl_idname,
                                  type='H', value='PRESS', ctrl=True, alt=True)
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new(ACT_OT_key_unlocked.bl_idname,
                                  type='K', value='PRESS', shift=True)
        addon_keymaps.append((km, kmi))


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    del bpy.types.Scene.anim_ctrl_tools
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
