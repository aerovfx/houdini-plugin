"""Pixibox HDA - SOP and LOP nodes for 3D generation in Houdini."""

import hou
import os
import tempfile
import json
from . import api

try:
    import hdefereval
    HDEFEREVAL_AVAILABLE = True
except ImportError:
    HDEFEREVAL_AVAILABLE = False


class PixiboxGeneratorNode:
    """Pixibox SOP generator node."""

    def __init__(self):
        """Initialize the node."""
        self.api = None
        self.generation_id = None
        self.output_url = None
        self.poll_count = 0
        self.max_polls = 300  # 10 minutes with 2-second intervals

    def cook(self, sop_node):
        """Cook the SOP node.

        Args:
            sop_node: The Houdini SOP node being cooked
        """
        try:
            # Get parameters
            api_key = sop_node.parm("api_key").eval()
            input_type = sop_node.parm("input_type").eval()
            input_value = sop_node.parm("input_value").eval()
            model = sop_node.parm("model").eval()
            export_format = sop_node.parm("export_format").eval()

            if not api_key:
                raise hou.NodeError("API key not set")

            # Initialize API
            self.api = api.PixiboxAPI(api_key)

            # Start generation
            hou.ui.setStatusMessage("Starting generation...", severity=hou.severityType.Message)

            if input_type == "0":  # Text
                success, gen_id, msg = self.api.generate("text_to_3d", input_value, model)
            else:  # Image
                if not os.path.exists(input_value):
                    raise hou.NodeError(f"Image file not found: {input_value}")
                success, gen_id, msg = self.api.generate("image_to_3d", input_value, model)

            if not success:
                raise hou.NodeError(f"Generation failed: {msg}")

            self.generation_id = gen_id
            hou.ui.setStatusMessage(f"Generation started: {gen_id}", severity=hou.severityType.Message)

            # Start polling
            self.poll_count = 0
            self._start_polling(sop_node, export_format)

        except Exception as e:
            raise hou.NodeError(f"Error: {str(e)}")

    def _start_polling(self, sop_node, export_format: str = "glb"):
        """Start the polling loop using deferred callbacks.

        Args:
            sop_node: The SOP node
            export_format: Format to download (glb, usda, usdz)
        """
        if not HDEFEREVAL_AVAILABLE:
            # Fallback: no hdefereval, just do blocking polling
            self._poll_generation_blocking(sop_node, export_format)
        else:
            # Use hdefereval to avoid blocking Houdini
            self._poll_generation_deferred(sop_node, export_format)

    def _poll_generation_deferred(self, sop_node, export_format: str):
        """Poll using hdefereval.executeDeferred (non-blocking).

        Args:
            sop_node: The SOP node
            export_format: Format to download
        """
        def poll_callback():
            try:
                status, output_url, msg = self.api.check_status(self.generation_id)

                if status == "completed":
                    if output_url:
                        if export_format == "glb":
                            self._download_and_import_glb(sop_node, output_url)
                        elif export_format in ("usda", "usdz"):
                            self._download_and_import_usd(sop_node, export_format)
                        else:
                            self._download_and_import_glb(sop_node, output_url)

                    hou.ui.setStatusMessage("Generation completed!", severity=hou.severityType.Message)
                    return

                elif status == "failed":
                    raise hou.NodeError(f"Generation failed: {msg}")

                else:
                    hou.ui.setStatusMessage(f"Status: {status}...", severity=hou.severityType.Message)
                    self.poll_count += 1

                    if self.poll_count < self.max_polls:
                        # Schedule next poll in 2 seconds
                        hdefereval.executeDeferred(poll_callback, 2.0)
                    else:
                        raise hou.NodeError("Generation timeout")

            except Exception as e:
                hou.ui.setStatusMessage(f"Error: {str(e)}", severity=hou.severityType.Error)

        # Start the first poll
        hdefereval.executeDeferred(poll_callback, 1.0)

    def _poll_generation_blocking(self, sop_node, export_format: str = "glb"):
        """Poll API for generation status (blocking).

        Args:
            sop_node: The SOP node
            export_format: Format to download (glb, usda, usdz)
        """
        import time

        while self.poll_count < self.max_polls:
            status, output_url, msg = self.api.check_status(self.generation_id)

            if status == "completed":
                if output_url:
                    if export_format == "glb":
                        self._download_and_import_glb(sop_node, output_url)
                    elif export_format in ("usda", "usdz"):
                        self._download_and_import_usd(sop_node, export_format)
                    else:
                        self._download_and_import_glb(sop_node, output_url)

                hou.ui.setStatusMessage("Generation completed!", severity=hou.severityType.Message)
                break

            elif status == "failed":
                raise hou.NodeError(f"Generation failed: {msg}")

            else:
                hou.ui.setStatusMessage(f"Status: {status}...", severity=hou.severityType.Message)

            # Wait before polling again
            time.sleep(2)
            self.poll_count += 1

        if self.poll_count >= self.max_polls:
            raise hou.NodeError("Generation timeout")

    def _download_and_import_glb(self, sop_node, url: str):
        """Download GLB and import into geometry.

        Args:
            sop_node: The SOP node
            url: Download URL
        """
        try:
            # Download to temp file
            temp_dir = tempfile.gettempdir()
            filepath = os.path.join(temp_dir, f"pixibox_{self.generation_id}.glb")

            success, msg = self.api.download_model(url, filepath)
            if not success:
                raise hou.NodeError(f"Download failed: {msg}")

            # Load geometry from file
            geo = hou.Geometry()
            geo.loadFromFile(filepath)

            # Get output geometry
            output_geo = sop_node.geometry()
            output_geo.clear()

            # Copy geometry
            for prim in geo.prims():
                output_geo.mergePrimitive(prim)

            # Clean up
            try:
                os.remove(filepath)
            except Exception:
                pass

        except Exception as e:
            raise hou.NodeError(f"Import error: {str(e)}")

    def _download_and_import_usd(self, sop_node, format_type: str):
        """Download USD and import into Solaris (if available).

        Args:
            sop_node: The SOP node
            format_type: 'usda' or 'usdz'
        """
        try:
            # Check if LOPs available
            try:
                from pxr import Usd
            except ImportError:
                raise hou.NodeError("USD/Solaris not available - use GLB format or upgrade Houdini")

            # Get USD URL
            success, usd_url, msg = self.api.export_usd(self.generation_id, format_type)
            if not success:
                raise hou.NodeError(f"Failed to get USD export: {msg}")

            # Download USD
            temp_dir = tempfile.gettempdir()
            ext = "usda" if format_type == "usda" else "usdz"
            filepath = os.path.join(temp_dir, f"pixibox_{self.generation_id}.{ext}")

            success, msg = self.api.download_usd(usd_url, filepath)
            if not success:
                raise hou.NodeError(f"Download failed: {msg}")

            # Store USD path as detail attribute
            output_geo = sop_node.geometry()
            output_geo.addAttrib(hou.attribType.Global, "pixibox_usd_path", filepath)

            # Try to import into Solaris if available
            try:
                from . import lop_utils
                parent_net = sop_node.parent()
                lop_node = None

                # Find or create LOP node
                for node in parent_net.children():
                    if node.type().name() == "pixibox_usd":
                        lop_node = node
                        break

                if lop_node:
                    lop_utils.import_to_solaris(lop_node, filepath)

            except (ImportError, Exception):
                # Silently skip if Solaris not available
                pass

        except Exception as e:
            raise hou.NodeError(f"USD import error: {str(e)}")


def cook_sop(node):
    """Entry point for SOP cooking.

    Args:
        node: The Houdini SOP node
    """
    generator = PixiboxGeneratorNode()
    generator.cook(node)
