# Yi Only Key Unlocked Channel

A Blender add-on for isolating selected controllers and inserting keyframes only on unlocked transform channels.

## Requirements

- Blender 4.3 or newer

## Features

- Works with selected pose bones in Pose Mode and selected objects in Object Mode.
- Toggles between isolating the current selection and revealing hidden bones or objects.
- Inserts keyframes at the current frame for unlocked Location, Rotation, and Scale channels.
- Supports Euler, Quaternion, and Axis-Angle rotation modes.
- Optionally keys numeric custom properties on the selected controllers.
- Lets you choose Blender's default interpolation, Constant, Linear, or Bezier interpolation.
- Supports Blender undo for its operators.

## Installation

1. Download `03-Yi_only_key_unlocked_channel.py` from this folder.
2. In Blender, open **Edit → Preferences → Add-ons**.
3. Open the menu in the upper-right and choose **Install from Disk**.
4. Select the downloaded Python file, then enable **Yi_only_key_unlocked_channel**.

## Usage

In the 3D View, open **N sidebar → Anim Tools → Yi_Only Key Unlocked Channel**.

Select the objects or pose bones you want to affect. In the Keyframe section, choose whether to include numeric custom properties and select an interpolation mode, then click **Key Unlocked Channels**. Keys are inserted at the current frame, only for channels that are not locked.

Use **Isolate Selected** to hide unselected objects or bones. Click it again to reveal them.

## Shortcuts

- `Ctrl+Alt+H` — Toggle isolation of the selected objects or bones.
- `Shift+K` — Key unlocked channels using the current panel settings.

The shortcuts apply in the 3D View and can be changed in Blender's keymap preferences.

## Notes

The add-on operates on the current selection. In Pose Mode it uses selected pose bones; in Object Mode it uses selected objects.
