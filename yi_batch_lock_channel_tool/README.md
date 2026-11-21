# Yi Batch Lock Channel Tool

A Blender add-on for batch locking or unlocking transform channels on selected controllers and applying a rotation mode.

- Version: 1.1.0
- Blender: 4.3 or newer

## Installation

1. Download [`02-yi_batch_lock_channel_tool.py`](./02-yi_batch_lock_channel_tool.py).
2. In Blender, open **Edit → Preferences → Add-ons**.
3. Open the menu in the upper-right, choose **Install from Disk**, and select the downloaded Python file.
4. Enable **Yi_Batch Lock Channel Tool**.

## Usage

In the 3D View, open **N sidebar → Anim Tools → Yi_Batch Lock Channel Tool**.

The tool operates on the current selection: selected pose bones in Pose Mode, or selected objects in other modes.

For each transform channel—Location, Rotation, and Scale—choose which axes to affect, then click **Lock** or **Unlock**. **Lock All** and **Unlock All** apply the operation to all three channels while respecting the axis toggles. For Rotation, the **W** toggle includes the quaternion or axis-angle W component.

To change rotation order, choose an Euler order, Quaternion, or Axis Angle, then click **Apply**. This updates the rotation mode of every selected target.

The operators support Blender undo. If no objects or pose bones are selected, the tool reports a warning and makes no changes.
