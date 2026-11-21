# Yi Blender Tools

A collection of Blender add-ons and Python scripts for animation and rigging workflows.

## Tools

### ⭐01- Yi Animation Selection Sets

Save and reuse pose-bone selection sets for armature rigs.

- Version: 2.7.2
- Blender: 4.2 or newer
- License: GPL-3.0-or-later
- Package: [`01-Yi_anim_selection_set-2.7.2.zip`](./01-Yi_anim_selection_set-2.7.2.zip)
- Details: [`yi_anim_selection_set/README.md`](./yi_anim_selection_set/README.md)

Install the ZIP from **Edit → Preferences → Get Extensions → Install from Disk**, then enable **Yi_anim_selection_set** if Blender does not enable it automatically.

### ⭐02- Yi Batch Lock Channel Tool

Batch-lock or unlock transform channels on selected objects or pose bones, and apply a rotation mode.

- Version: 1.1.0
- Blender: 4.3 or newer
- Script: [`02-yi_batch_lock_channel_tool.py`](./02-yi_batch_lock_channel_tool.py)
- Details: [`yi_batch_lock_channel_tool/README.md`](./yi_batch_lock_channel_tool/README.md)

Install the Python file from **Edit → Preferences → Add-ons → Install from Disk**. Find the tool in the 3D View sidebar under **Anim Tools → Yi_Batch Lock Channel Tool**.

### ⭐03- Bone Collection Backup

A Blender 4.3 add-on for exporting and restoring selected bones and Bone Collection memberships with JSON.

- Script: [`04-Yi_bone_collection_backup.py`](./04-Yi_bone_collection_backup.py)

### Additional Scripts

The repository also includes standalone scripts for specific rigging and animation tasks:

- [`03-Yi_only_key_unlocked_channel.py`](./03-Yi_only_key_unlocked_channel.py) — key unlocked channels.
- [`script-001-disable_selected_bone_deform.py`](./script-001-disable_selected_bone_deform.py) — disable deformation on selected bones.
- [`script-002-select_by_name_pose_mode.py`](./script-002-select_by_name_pose_mode.py) — select bones by name in Pose Mode.
- [`script-003-rigify_custom_shapes_preserve.py`](./script-003-rigify_custom_shapes_preserve.py) — preserve Rigify custom shapes.
- [`script-004-batch_assign_parent_bone.py`](./script-004-batch_assign_parent_bone.py) — batch-assign a parent bone.
- [`script-005-rig_ui_rigify_generic_remove_tweak_remove_ikstretch.py`](./script-005-rig_ui_rigify_generic_remove_tweak_remove_ikstretch.py) — customize the Rigify Generic rig UI by removing Tweak and IK Stretch controls.

## Installing Standalone Scripts

Standalone `.py` files are scripts, not necessarily installable add-ons. Unless a script’s own instructions say otherwise, open Blender’s **Scripting** workspace, load the script in the Text Editor, and click **Run Script**. Save a copy of your `.blend` file before running scripts that modify a rig.

## Compatibility

Blender version requirements vary by tool. Check the relevant tool section or its README before installing or running it.

## Repository

[View the source on GitHub](https://github.com/foufouzi/yi-blender-add-on)
