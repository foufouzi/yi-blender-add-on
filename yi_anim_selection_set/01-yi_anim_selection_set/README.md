# Yi Animation Selection Sets

A Blender extension for saving and reusing pose-bone selection sets per armature rig.

- Version: 2.7.2
- Requirements: Blender 4.2 or newer
- License: GPL-3.0-or-later

## Installation

1. Download the [Yi Animation Selection Sets 2.7.2 extension ZIP](./01-Yi_anim_selection_set-2.7.2.zip).
2. In Blender, open **Edit → Preferences → Get Extensions**.
3. Open the menu in the upper-right, choose **Install from Disk**, and select the downloaded ZIP.
4. Enable **Yi_anim_selection_set** if Blender does not enable it automatically.

## Using Selection Sets

Select an armature and enter **Pose Mode**. Open **N sidebar → Item → Selection Sets**. Click **Add Selection Set** to save the currently selected pose bones.

Each set row provides these controls:

- **Star:** Solo the set, showing only its bones. Toggle it off to restore the previous bone visibility.
- **Eye:** Toggle visibility for the bones in the set.
- **Color swatch:** Choose a color tag for the set.
- **Set name:** Click to select the saved bones; Shift-click to add them to the current selection.
- **+ / −:** Add the selected bones to the set or remove them from it.
- **Up / Down:** Move the set in the list. The order is saved.
- **X:** Remove the set.

## Horizontal Set Strip

Click **Open Set Strip Window** at the bottom of the Selection Sets panel to duplicate the current 3D View into a separate window. In that window, open **N sidebar → Item → Set Strip** for a compact horizontal row of set-name buttons. Close the duplicated window when you are done.

The **Shift+Q** shortcut opens the full Selection Sets popup in the 3D View while in Pose Mode. You can change this shortcut in the extension preferences.

## Storage and Compatibility

Selection sets are stored in a per-user JSON file outside the `.blend` file and keyed by rig name, so they are available across shots for that user. The add-on can also import legacy selection sets stored in a `.blend` file.
