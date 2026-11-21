# Yi Bone Collection Backup

A Blender add-on for exporting selected armature bones to a JSON backup and restoring them to an armature. The backup can include bone hierarchy, Bone Collection memberships, and pose-bone constraints.

## Requirements

- Blender 4.3 or newer

## Features

- Export selected bones from Edit Mode or Pose Mode to a `.json` file.
- Save each bone's head and tail positions, roll, parent relationship, connection state, deformation setting, and inheritance settings.
- Save the Bone Collection memberships of exported bones.
- Optionally export and restore pose-bone constraints, including supported constraint settings and datablock targets.
- Import in **Add Missing Only** or **Overwrite Existing** mode.
- Read backup file format versions 1 and 2.
- Supports Blender undo for the import operation.

## Installation

1. Download `04-Yi_bone_collection_backup.py` from this folder.
2. In Blender, open **Edit → Preferences → Add-ons**.
3. Open the menu in the upper-right and choose **Install from Disk**.
4. Select the downloaded Python file, then enable **Yi Bone Collection Backup**.

## Usage

In the 3D View, select or activate the armature object. To export, select the bones in Edit Mode or Pose Mode, then open **N sidebar → Rigging → Yi Bone Backup Tool**.

Keep **Include Bone Constraints** enabled to include pose-bone constraints in the backup. Click **Export Selected Bones** and choose where to save the JSON file. Export requires at least one selected bone.

To restore a backup, make the destination armature active, click **Import Bone Backup**, and choose the JSON file. The default conflict option is **Add Missing Only**. Choose **Overwrite Existing** when you want matching same-name bones to be updated from the backup.

## Import Behavior

- **Add Missing Only** keeps existing same-name bones and their constraints unchanged, and adds missing bones from the file.
- **Overwrite Existing** updates matching bones and replaces their constraints with those in the backup when constraints are included.
- Bone Collection memberships for imported or overwritten bones are restored from the backup. Missing Bone Collections are created as needed.
- When a constraint target cannot be found in the destination file, the add-on reports the missing target or restore warning in Blender's System Console.

Save a copy of your `.blend` file before importing, especially when using **Overwrite Existing**.

## Configuration

The sidebar panel appears under the **Rigging** tab by default. To place it under a different 3D View sidebar tab, change `PANEL_CATEGORY` near the top of the Python file before installing or reloading the add-on.

## Backup Format

The add-on exports JSON files using the `blender_bone_collection_backup` format. Keep the JSON file intact so the add-on can validate and restore it.
