"""Pixibox shelf tools for Houdini."""

import hou
import os
import tempfile
from . import api
from . import bridge


def show_generate_dialog():
    """Show dialog for Pixibox generation."""
    try:
        api_key = hou.ui.readInput(
            message="Enter your Pixibox API Key:",
            buttons=("OK", "Cancel"),
            title="Pixibox API Key"
        )[1]

        if not api_key:
            return

        # Input type selection
        input_type = hou.ui.selectFromList(
            ["Text Prompt", "Image File"],
            message="Select input type:",
            title="Pixibox Generation"
        )

        if input_type is None:
            return

        if input_type[0] == 0:  # Text
            prompt = hou.ui.readInput(
                message="Enter text prompt:",
                buttons=("OK", "Cancel"),
                title="Text Prompt"
            )[1]
            if not prompt:
                return
            input_value = prompt
            input_type_str = "text_to_3d"
        else:  # Image
            file_chooser = hou.ui.selectFile(
                title="Select Image File",
                file_type=hou.fileType.Image
            )
            if not file_chooser:
                return
            input_value = file_chooser
            input_type_str = "image_to_3d"

        # Model selection
        models = [
            "Trellis 2 (Fast)",
            "Hunyuan 3D",
            "NVIDIA Edify 3D"
        ]

        model_choice = hou.ui.selectFromList(
            models,
            message="Select AI model:",
            title="Pixibox Models"
        )

        if model_choice is None:
            return

        model_map = {
            0: "trellis-2",
            1: "hunyuan-3d",
            2: "nvidia-edify"
        }
        model = model_map[model_choice[0]]

        # Show info
        hou.ui.displayMessage(
            f"Generation started!\n"
            f"Input: {input_type_str}\n"
            f"Model: {model}\n"
            f"Check the status bar for updates."
        )

    except Exception as e:
        hou.ui.displayMessage(f"Error: {str(e)}", severity=hou.severityType.Error)


def create_pixibox_node():
    """Create a Pixibox SOP node in the current network."""
    try:
        # Get the current node and try to get its parent network
        selection = hou.selectedNodes()

        if selection:
            parent = selection[0].parent()
        else:
            # Try to get the current network
            parent = hou.node("/obj")

        if parent is None or not isinstance(parent, hou.ObjNode):
            hou.ui.displayMessage(
                "Please select a node or work in an Object network",
                severity=hou.severityType.Error
            )
            return

        # Create a new SOP network
        geo = parent.createNode("geo", "pixibox_generation")

        # Create the Pixibox SOP inside
        # This would reference the HDA we create
        sop = geo.createNode("pixibox_generate", "pixibox1")

        hou.ui.displayMessage("Pixibox SOP created! Configure parameters and cook.")

    except Exception as e:
        hou.ui.displayMessage(
            f"Error creating node: {str(e)}",
            severity=hou.severityType.Error
        )


def import_usd_dialog():
    """Show dialog to import latest generation as USD."""
    try:
        api_key = hou.ui.readInput(
            message="Enter your Pixibox API Key:",
            buttons=("OK", "Cancel"),
            title="Pixibox API Key"
        )[1]

        if not api_key:
            return

        api_client = api.PixiboxAPI(api_key)

        # Get recent scenes
        success, scenes, msg = api_client.get_scenes(limit=10)
        if not success:
            hou.ui.displayMessage(f"Failed to fetch scenes: {msg}", severity=hou.severityType.Error)
            return

        if not scenes:
            hou.ui.displayMessage("No scenes available", severity=hou.severityType.Warning)
            return

        # Build scene list
        scene_names = [f"{s.get('name', 'Untitled')} ({s.get('id', 'N/A')})" for s in scenes]
        selection = hou.ui.selectFromList(
            scene_names,
            message="Select scene to import as USD:",
            title="Import USD"
        )

        if selection is None:
            return

        selected_scene = scenes[selection[0]]
        scene_id = selected_scene.get("id")

        # Choose format
        format_choice = hou.ui.selectFromList(
            ["USDA (Recommended)", "USDZ (Apple)"],
            message="Select USD format:",
            title="Format"
        )

        if format_choice is None:
            return

        format_type = "usda" if format_choice[0] == 0 else "usdz"

        # Download and save
        success, download_url, msg = api_client.export_usd(scene_id, format_type)
        if not success:
            hou.ui.displayMessage(f"Failed to get USD: {msg}", severity=hou.severityType.Error)
            return

        save_path = hou.ui.selectFile(
            title="Save USD File",
            file_type=hou.fileType.Directory
        )

        if not save_path:
            return

        filename = f"{selected_scene.get('name', 'untitled')}.{format_type}"
        filepath = os.path.join(save_path, filename)

        success, msg = api_client.download_usd(download_url, filepath)
        if success:
            hou.ui.displayMessage(f"USD imported to:\n{filepath}", severity=hou.severityType.Message)
        else:
            hou.ui.displayMessage(f"Download failed: {msg}", severity=hou.severityType.Error)

    except Exception as e:
        hou.ui.displayMessage(f"Error: {str(e)}", severity=hou.severityType.Error)


def start_live_bridge():
    """Start Live Bridge connection."""
    try:
        if bridge.is_live_bridge_connected():
            hou.ui.displayMessage("Live Bridge already connected", severity=hou.severityType.Message)
            return

        api_key = hou.ui.readInput(
            message="Enter your Pixibox API Key:",
            buttons=("OK", "Cancel"),
            title="Live Bridge"
        )[1]

        if not api_key:
            return

        success, msg = bridge.start_live_bridge(api_key)
        severity = hou.severityType.Message if success else hou.severityType.Error
        hou.ui.displayMessage(f"Live Bridge: {msg}", severity=severity)

        if success:
            # Register message drain callback
            _register_message_drain_callback()

    except Exception as e:
        hou.ui.displayMessage(f"Error: {str(e)}", severity=hou.severityType.Error)


def stop_live_bridge():
    """Stop Live Bridge connection."""
    try:
        success, msg = bridge.stop_live_bridge()
        severity = hou.severityType.Message if success else hou.severityType.Error
        hou.ui.displayMessage(f"Live Bridge: {msg}", severity=severity)
    except Exception as e:
        hou.ui.displayMessage(f"Error: {str(e)}", severity=hou.severityType.Error)


def toggle_live_bridge():
    """Toggle Live Bridge connection."""
    try:
        if bridge.is_live_bridge_connected():
            stop_live_bridge()
        else:
            start_live_bridge()
    except Exception as e:
        hou.ui.displayMessage(f"Error: {str(e)}", severity=hou.severityType.Error)


def browse_scenes_dialog():
    """Open scene browser dialog."""
    try:
        api_key = hou.ui.readInput(
            message="Enter your Pixibox API Key:",
            buttons=("OK", "Cancel"),
            title="Pixibox API Key"
        )[1]

        if not api_key:
            return

        api_client = api.PixiboxAPI(api_key)

        # Get scenes
        success, scenes, msg = api_client.get_scenes(limit=50)
        if not success:
            hou.ui.displayMessage(f"Failed to fetch scenes: {msg}", severity=hou.severityType.Error)
            return

        # Build display list
        scene_info = []
        for scene in scenes:
            info = f"{scene.get('name', 'Untitled')} - {scene.get('id', 'N/A')}"
            scene_info.append(info)

        # Show list
        hou.ui.displayMessage(
            f"Found {len(scenes)} scenes\n\n" + "\n".join(scene_info[:10]),
            severity=hou.severityType.Message
        )

    except Exception as e:
        hou.ui.displayMessage(f"Error: {str(e)}", severity=hou.severityType.Error)


def _register_message_drain_callback():
    """Register a periodic callback to drain Live Bridge messages.

    This handles dcc_push and other events from the bridge.
    """
    try:
        import hdefereval

        def drain_messages():
            """Drain and process messages from the Live Bridge."""
            try:
                live_bridge = bridge.get_live_bridge()
                if not live_bridge or not live_bridge.is_connected():
                    return

                messages = live_bridge.get_messages()
                for msg in messages:
                    msg_type = msg.get("type")
                    data = msg.get("data", {})

                    if msg_type == "dcc_push":
                        # Handle dcc_push event: download models and import
                        models = data.get("models", [])
                        for model_info in models:
                            model_url = model_info.get("url")
                            model_format = model_info.get("format", "glb")
                            if model_url:
                                _import_dcc_push_model(model_url, model_format)

                    elif msg_type == "generation_complete":
                        # Log generation completion
                        gen_id = data.get("generation_id", "?")
                        hou.ui.setStatusMessage(
                            f"Pixibox: Generation complete {gen_id}",
                            severity=hou.severityType.Message
                        )

                    elif msg_type == "generation_failed":
                        # Log generation failure
                        gen_id = data.get("generation_id", "?")
                        err = data.get("errorMessage", "unknown")
                        hou.ui.setStatusMessage(
                            f"Pixibox: Generation failed {gen_id} - {err}",
                            severity=hou.severityType.Error
                        )

            except Exception as e:
                hou.ui.setStatusMessage(f"Bridge message drain error: {str(e)}", severity=hou.severityType.Warning)

            # Schedule next drain in 0.5 seconds
            if bridge.is_live_bridge_connected():
                hdefereval.executeDeferred(drain_messages, 0.5)

        # Start the drain loop
        hdefereval.executeDeferred(drain_messages, 0.5)

    except ImportError:
        # hdefereval not available, fall back to status message
        hou.ui.setStatusMessage("Live Bridge connected (message drain unavailable)", severity=hou.severityType.Message)


def _import_dcc_push_model(url: str, model_format: str):
    """Import a model from dcc_push event.

    Args:
        url: Download URL
        model_format: 'glb' or 'usda'
    """
    try:
        temp_dir = tempfile.gettempdir()

        if model_format == "glb":
            filename = "pixibox_live_push.glb"
            filepath = bridge.download_glb_for_import(url, filename)
            if filepath:
                # Load into current geometry
                geo = hou.Geometry()
                geo.loadFromFile(filepath)
                hou.ui.displayMessage(f"Imported GLB from Live Bridge: {filepath}", severity=hou.severityType.Message)
        elif model_format in ("usda", "usdz"):
            filename = f"pixibox_live_push.{model_format}"
            filepath = bridge.download_usd_for_import(url, filename)
            if filepath:
                hou.ui.displayMessage(f"Imported USD from Live Bridge: {filepath}", severity=hou.severityType.Message)

    except Exception as e:
        hou.ui.setStatusMessage(f"dcc_push import error: {str(e)}", severity=hou.severityType.Warning)


if __name__ == "__main__":
    show_generate_dialog()
