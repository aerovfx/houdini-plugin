"""Pixibox Solaris/LOP integration for Houdini USD workflows."""

import hou
import os
import tempfile
from typing import Optional, Tuple
from . import api


class PixiboxSolarisNode:
    """Custom LOP node for Pixibox USD integration in Solaris."""

    def __init__(self):
        """Initialize Solaris node handler."""
        self.api = None
        self.lop_node = None

    def cook(self, lop_node):
        """Cook the LOP node with Pixibox scene.

        Args:
            lop_node: The Houdini LOP node being cooked
        """
        try:
            # Check if LOPs available (Houdini FX/Solaris only)
            if not self._check_lops_available():
                raise hou.NodeError("Solaris/LOPs not available in this Houdini version")

            # Get parameters
            api_key = lop_node.parm("api_key").eval()
            scene_id = lop_node.parm("scene_id").eval()
            import_mode = lop_node.parm("import_mode").eval()  # 0=sublayer, 1=reference

            if not api_key:
                raise hou.NodeError("API key not set")

            if not scene_id:
                raise hou.NodeError("Scene ID not set")

            # Initialize API
            self.api = api.PixiboxAPI(api_key)
            self.lop_node = lop_node

            # Fetch USD from Pixibox
            success, usd_url, msg = self.api.export_usd(scene_id, "usda")
            if not success:
                raise hou.NodeError(f"Failed to get USD export: {msg}")

            # Download USD to temp file
            temp_dir = tempfile.gettempdir()
            usd_path = os.path.join(temp_dir, f"pixibox_{scene_id}.usda")

            success, msg = self.api.download_usd(usd_url, usd_path)
            if not success:
                raise hou.NodeError(f"Failed to download USD: {msg}")

            # Import into Solaris stage
            import_mode_str = "sublayer" if import_mode == 0 else "reference"
            self._import_to_solaris(lop_node, usd_path, import_mode_str)

            # Set status
            lop_node.setColor(hou.Color((0.0, 0.7, 0.0)))
            hou.ui.setStatusMessage(
                f"Pixibox USD imported: {scene_id}",
                severity=hou.severityType.Message
            )

        except Exception as e:
            raise hou.NodeError(f"Solaris cook error: {str(e)}")

    def _import_to_solaris(self, lop_node, usd_path: str, mode: str = "sublayer"):
        """Import USD file into Solaris stage.

        Args:
            lop_node: The LOP node
            usd_path: Path to USD file
            mode: 'sublayer' or 'reference'
        """
        try:
            from pxr import Usd, Sdf

            # Get the current stage
            stage = lop_node.stage()

            if stage is None:
                raise RuntimeError("No USD stage available in LOP node")

            # Get prim path for import
            prim_path = lop_node.parm("prim_path").eval()
            if not prim_path:
                prim_path = "/pixibox_import"

            if mode == "sublayer":
                # Add as sublayer
                root_layer = stage.GetRootLayer()
                root_layer.subLayerPaths.append(usd_path)
            else:
                # Add as reference
                if not stage.GetPrimAtPath(prim_path):
                    stage.DefinePrim(prim_path, "Xform")

                prim = stage.GetPrimAtPath(prim_path)
                prim.GetReferences().AddExternalReference(usd_path)

            hou.ui.setStatusMessage(
                f"USD {mode}ed to {prim_path}",
                severity=hou.severityType.Message
            )

        except Exception as e:
            raise RuntimeError(f"Solaris import error: {str(e)}")

    @staticmethod
    def _check_lops_available() -> bool:
        """Check if LOPs/Solaris is available in this Houdini version.

        Returns:
            True if LOPs available, False otherwise
        """
        try:
            from pxr import Usd
            return True
        except ImportError:
            return False


def import_to_solaris(lop_node, usd_path: str, mode: str = "sublayer") -> Tuple[bool, str]:
    """Import USD file into current Solaris context.

    Args:
        lop_node: The LOP node to import into
        usd_path: Path to USD file
        mode: 'sublayer' or 'reference'

    Returns:
        Tuple of (success, message)
    """
    try:
        node = PixiboxSolarisNode()
        node._import_to_solaris(lop_node, usd_path, mode)
        return True, f"Imported to {mode}"
    except Exception as e:
        return False, str(e)


def export_from_solaris(lop_node, output_path: str) -> Tuple[bool, str]:
    """Export Solaris stage to USD file.

    Args:
        lop_node: The LOP node to export from
        output_path: Output USD file path

    Returns:
        Tuple of (success, message)
    """
    try:
        stage = lop_node.stage()
        if stage is None:
            return False, "No USD stage in LOP node"

        # Save stage to USD
        stage.GetRootLayer().Export(output_path)
        return True, f"Exported to {output_path}"

    except Exception as e:
        return False, str(e)


def convert_pbr_to_materialsx(
    lop_node,
    pbr_material_name: str
) -> Tuple[bool, str]:
    """Convert Pixibox PBR material to Houdini MaterialX.

    Args:
        lop_node: The LOP node
        pbr_material_name: Name of PBR material to convert

    Returns:
        Tuple of (success, message)
    """
    try:
        from pxr import Usd, UsdShade

        stage = lop_node.stage()
        if stage is None:
            return False, "No USD stage in LOP node"

        # Find material prim
        material_path = f"/materials/{pbr_material_name}"
        material_prim = stage.GetPrimAtPath(material_path)

        if not material_prim:
            return False, f"Material {pbr_material_name} not found"

        # Convert to MaterialX-compatible structure
        # Create MaterialX material node
        mx_material_path = f"/materialx/{pbr_material_name}"
        mx_prim = UsdShade.Material.Define(stage, mx_material_path)

        # Map PBR attributes to MaterialX
        # This is a simplified conversion - full mapping depends on material complexity
        pbr_attrs = {
            "baseColor": ("base_color", "float3"),
            "metallic": ("metallic", "float"),
            "roughness": ("roughness", "float"),
            "normal": ("normal", "normal3"),
        }

        for pbr_attr, (mx_attr, mx_type) in pbr_attrs.items():
            pbr_val = material_prim.GetAttribute(pbr_attr)
            if pbr_val:
                mx_prim.CreateAttribute(mx_attr, mx_type).Set(pbr_val.Get())

        return True, f"Converted {pbr_material_name} to MaterialX"

    except Exception as e:
        return False, f"MaterialX conversion error: {str(e)}"


def cook_lop(node):
    """Entry point for LOP cooking.

    Args:
        node: The Houdini LOP node
    """
    generator = PixiboxSolarisNode()
    generator.cook(node)
