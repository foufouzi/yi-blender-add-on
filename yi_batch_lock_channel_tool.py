bl_info = {
    "name": "Yi_Batch Lock Channel Tool",
    "author": "webby",
    "version": (1, 1, 0),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar (N) > Anim Tools",
    "description": "Lock / unlock Location, Rotation, Scale on selected controllers",
    "category": "Animation",
}

import bpy


CHANNELS = {
    'LOC': ("lock_location", "Location", "lrt_loc"),
    'ROT': ("lock_rotation", "Rotation", "lrt_rot"),
    'SCL': ("lock_scale", "Scale", "lrt_scl"),
}


def get_targets(context):
    """Pose Mode -> selected pose bones, otherwise -> selected objects."""
    if context.mode == 'POSE':
        return list(context.selected_pose_bones or [])
    return list(context.selected_objects)


class ANIM_OT_set_transform_lock(bpy.types.Operator):
    """Lock or unlock transform channels on selected controllers"""
    bl_idname = "anim.set_transform_lock"
    bl_label = "Set Transform Lock"
    bl_options = {'REGISTER', 'UNDO'}

    channel: bpy.props.EnumProperty(
        name="Channel",
        items=[
            ('LOC', "Location", ""),
            ('ROT', "Rotation", ""),
            ('SCL', "Scale", ""),
            ('ALL', "All", ""),
        ],
        default='ROT',
    )
    lock: bpy.props.BoolProperty(name="Lock", default=True)

    def execute(self, context):
        s = context.scene
        targets = get_targets(context)
        if not targets:
            self.report({'WARNING'}, "沒有選取任何 controller")
            return {'CANCELLED'}

        keys = list(CHANNELS) if self.channel == 'ALL' else [self.channel]

        for t in targets:
            for key in keys:
                attr, _label, prefix = CHANNELS[key]
                lock_arr = getattr(t, attr)
                for i, axis in enumerate("xyz"):
                    if getattr(s, f"{prefix}_{axis}"):
                        lock_arr[i] = self.lock

                if key == 'ROT' and s.lrt_rot_w:
                    if self.lock:
                        t.lock_rotations_4d = True
                    t.lock_rotation_w = self.lock

        state = "鎖定" if self.lock else "解鎖"
        names = "全部" if self.channel == 'ALL' else CHANNELS[self.channel][1]
        self.report({'INFO'}, f"已{state} {len(targets)} 個 controller 的 {names}")
        return {'FINISHED'}


ROT_MODE_ITEMS = [
    ('XYZ', "XYZ Euler", ""),
    ('XZY', "XZY Euler", ""),
    ('YXZ', "YXZ Euler", ""),
    ('YZX', "YZX Euler", ""),
    ('ZXY', "ZXY Euler", ""),
    ('ZYX', "ZYX Euler", ""),
    ('QUATERNION', "Quaternion", ""),
    ('AXIS_ANGLE', "Axis Angle", ""),
]


class ANIM_OT_set_rotation_order(bpy.types.Operator):
    """Change rotation order (mode) of selected controllers"""
    bl_idname = "anim.set_rotation_order"
    bl_label = "Set Rotation Order"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        targets = get_targets(context)
        if not targets:
            self.report({'WARNING'}, "沒有選取任何 controller")
            return {'CANCELLED'}

        new_order = context.scene.lrt_rot_order
        for t in targets:
            t.rotation_mode = new_order

        self.report({'INFO'}, f"已將 {len(targets)} 個 controller 改成 {new_order}")
        return {'FINISHED'}


class VIEW3D_PT_lock_transform_tool(bpy.types.Panel):
    bl_label = "Yi_Batch Lock Channel Tool"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Anim Tools"

    def draw_header(self, context):
        self.layout.label(text="", icon='SOLO_ON')

    def draw(self, context):
        layout = self.layout
        s = context.scene

        for key, (_attr, label, prefix) in CHANNELS.items():
            box = layout.box()
            box.label(text=label)

            row = box.row(align=True)
            row.prop(s, f"{prefix}_x", toggle=True)
            row.prop(s, f"{prefix}_y", toggle=True)
            row.prop(s, f"{prefix}_z", toggle=True)
            if key == 'ROT':
                row.prop(s, "lrt_rot_w", toggle=True)

            row = box.row(align=True)
            op = row.operator("anim.set_transform_lock", text="Lock", icon='LOCKED')
            op.channel, op.lock = key, True
            op = row.operator("anim.set_transform_lock", text="Unlock", icon='UNLOCKED')
            op.channel, op.lock = key, False

        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.4
        op = row.operator("anim.set_transform_lock", text="Lock All", icon='LOCKED')
        op.channel, op.lock = 'ALL', True
        op = row.operator("anim.set_transform_lock", text="Unlock All", icon='UNLOCKED')
        op.channel, op.lock = 'ALL', False

        layout.separator()
        box = layout.box()
        box.label(text="Rotation Order")
        row = box.row(align=True)
        row.prop(s, "lrt_rot_order", text="")
        row.operator("anim.set_rotation_order", text="Apply", icon='ORIENTATION_GIMBAL')

        mode = "Pose Bones" if context.mode == 'POSE' else "Objects"
        layout.label(text=f"目標：選取的 {mode}", icon='INFO')


classes = (
    ANIM_OT_set_transform_lock,
    ANIM_OT_set_rotation_order,
    VIEW3D_PT_lock_transform_tool,
)

PROPS = []
for _key, (_attr, _label, _prefix) in CHANNELS.items():
    for _axis in "xyz":
        PROPS.append((f"{_prefix}_{_axis}", _axis.upper()))


def register():
    for c in classes:
        bpy.utils.register_class(c)
    for name, label in PROPS:
        setattr(bpy.types.Scene, name, bpy.props.BoolProperty(name=label, default=True))
    bpy.types.Scene.lrt_rot_w = bpy.props.BoolProperty(
        name="W", default=False,
        description="Quaternion / Axis Angle W component")
    bpy.types.Scene.lrt_rot_order = bpy.props.EnumProperty(
        name="Rotation Order", items=ROT_MODE_ITEMS, default='XYZ')


def unregister():
    for name, _label in PROPS:
        delattr(bpy.types.Scene, name)
    del bpy.types.Scene.lrt_rot_w
    del bpy.types.Scene.lrt_rot_order
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
