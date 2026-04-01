# Pixibox Houdini Digital Assets (HDAs)

This directory contains custom Houdini Digital Assets (HDAs) for the Pixibox plugin.

## HDA Compilation

HDAs must be compiled in Houdini Desktop before use. The source files are provided as `.py` modules that define the node structure.

### Pixibox_Generate HDA

**Purpose**: Batch generation node for SOPs (Surface Operators) context

**Features**:
- Prompt or image input selection
- Multiple generation options in single node
- Auto-import to Solaris option
- Batch processing support

### How to Compile

1. Open Houdini Desktop (not Houdini Indie)
2. Create a test node network or use an existing project
3. Create the node you want to save as HDA
4. Right-click the node → **Save as Digital Asset...**
5. Set:
   - **Name**: `Pixibox_Generate`
   - **Label**: `Pixibox Generate`
   - **Location**: Choose `otls/pixibox_generate.hda`
6. Click **Save**
7. HDA is now compiled and ready to use

### Using Compiled HDAs

Once compiled:
1. The `.hda` file appears in the `otls/` directory
2. Houdini auto-loads it when plugin is installed
3. Node appears in **TAB menu → Pixibox** section

### HDA Parameters

When creating your HDA, expose these parameters:

**Inputs**:
- `prompt` (String): Text-to-3D prompt
- `image_path` (File): Image file path for image-to-3D
- `generation_mode` (Menu): "text-to-3d" or "image-to-3d"
- `ai_model` (Menu): Model selection
- `auto_import` (Toggle): Auto-import to Solaris when complete

**Outputs**:
- Output 0: Geometry (packed primitives)
- Output 1: Material assignment details
- Output 2: Metadata (generation ID, timing, etc)

### Development Notes

- HDAs are stored in binary `.hda` format (not editable directly)
- To modify HDA:
  1. Open it in Houdini
  2. Edit nodes inside
  3. Save again as HDA
- Type definitions can be customized after compilation
- HDAs are version-controlled in Git (binary files)

### Documentation

For more information on Houdini Digital Assets:
- [SideFX HDAs Documentation](https://www.sidefx.com/docs/houdini/assets/)
- [HDA Best Practices](https://www.sidefx.com/docs/houdini/assets/create.html)
