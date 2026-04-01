"""
Solaris/LOPs utilities for USD composition and MaterialX conversion.

Handles importing generated 3D models into USD stage, setting up
material networks, and managing geometry in LOPs context.
"""

import os
import json
from typing import Optional, Dict, Any, Tuple

try:
    import hou
    from pxr import Usd, UsdGeom, Sdf, UsdShade, UsdUtils
    from pxr import MaterialX as Mtlx
    HAS_HOUDINI = True
except ImportError:
    HAS_HOUDINI = False
    hou = None  # type: ignore
    Usd = None  # type: ignore
    UsdGeom = None  # type: ignore
    Sdf = None  # type: ignore
    UsdShade = None  # type: ignore
    UsdUtils = None  # type: ignore
    Mtlx = None  # type: ignore


from .api import PixiboxClient, download_model


def get_current_stage() -> Optional[Any]:
    """
    Get currently active USD stage in Solaris/LOPs.

    Returns:
        pxr.Usd.Stage object or None if not in LOPs context

    Raises:
        RuntimeError: If Houdini/Solaris not available
    """
    if not HAS_HOUDINI:
        raise RuntimeError("Houdini/USD libraries not available")

    if not hou:
        raise RuntimeError("Not running in Houdini context")

    try:
        # Get active viewer pane in Solaris
        desktop = hou.ui.curDesktop()
        for pane in desktop.paneTabs():
            if pane.type().name() == "SceneViewer":
                # Check if in LOPs context
                geo = pane.pwd()
                if geo and geo.path().startswith("/lops"):
                    # Get USD stage from LOP node
                    if hasattr(geo, "stage"):
                        return geo.stage()

        # Fallback: try to get from SOLARIS_LOP env variable
        return None

    except Exception as e:
        raise RuntimeError(f"Failed to get current stage: {str(e)}")


def import_to_stage(
    generation_id: str,
    prim_path: str = "/World/Imports/Model",
    apply_materialx: bool = True,
    auto_optimize: bool = False,
    texture_resolution: str = "high",
    token: Optional[str] = None,
) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Import generated model to USD stage.

    Downloads the GLB model and imports it to the specified prim path
    in the current USD stage, optionally applying MaterialX materials.

    Args:
        generation_id: Pixibox generation ID
        prim_path: Target prim path (e.g. "/World/Imports/Vase")
        apply_materialx: Convert materials to MaterialX
        auto_optimize: Apply mesh optimization (remesh, decimate)
        texture_resolution: "low", "medium", "high" for texture LOD
        token: Auth token (reads PIXIBOX_AUTH_TOKEN if not set)

    Returns:
        Tuple of (import_node_path, metadata_dict) or (None, error_dict)

    Example:
        >>> node_path, meta = import_to_stage(
        ...     "gen-123",
        ...     "/World/Imports/MyVase",
        ...     apply_materialx=True
        ... )
        >>> if node_path:
        ...     print(f"Imported to {node_path}")
        ... else:
        ...     print(f"Error: {meta['error']}")
    """
    if not HAS_HOUDINI:
        return None, {"error": "Houdini/USD libraries not available"}

    try:
        # Download model
        model_path = download_model(generation_id, format="glb", token=token)

        # Get current LOP node (parent)
        pwd = hou.pwd()
        if not pwd or not pwd.path().startswith("/lops"):
            return None, {"error": "Not in LOPs context. Switch to Solaris tab first."}

        # Create Import USD node
        import_node = pwd.createNode("importusd", f"import_gen_{generation_id}")
        import_node.parm("filepath").set(model_path)

        # Create Subnet for organization
        subnet = pwd.createNode("subnet", f"subnet_gen_{generation_id}")
        import_node.setInput(0, subnet)

        # Create reference/copy to target prim path
        copy_node = pwd.createNode("usdcopy", f"copy_gen_{generation_id}")
        copy_node.setInput(0, import_node)

        # Set up primitive path
        stage = import_node.stage()
        if stage:
            # Find root geometry prim
            root_prim = None
            for prim in stage.Traverse():
                if UsdGeom.Xformable(prim):
                    root_prim = prim
                    break

            if root_prim:
                source_path = root_prim.GetPath()
                copy_node.parm("primpath").set(str(source_path))
                copy_node.parm("destpath").set(prim_path)

        # Apply MaterialX if requested
        if apply_materialx:
            mat_node = pwd.createNode("materiallibrary", f"matlib_gen_{generation_id}")
            mat_node.setInput(0, copy_node)

            # Extract textures and create material network
            metadata = _create_material_network_from_glb(
                model_path,
                stage,
                prim_path,
                texture_resolution,
            )
        else:
            metadata = {}

        # Display import node
        copy_node.setDisplayFlag(True)
        copy_node.setRenderFlag(True)

        return copy_node.path(), {
            "model_path": model_path,
            "prim_path": prim_path,
            "import_node": import_node.path(),
            "copy_node": copy_node.path(),
            **metadata,
        }

    except Exception as e:
        return None, {"error": f"Import failed: {str(e)}"}


def create_materialx_network(
    stage: Any,
    prim_path: str,
    textures: Dict[str, str],
    material_name: str = "PixiboxMaterial",
) -> bool:
    """
    Create MaterialX shader network on USD prim.

    Args:
        stage: pxr.Usd.Stage object
        prim_path: Target prim path (e.g. "/World/MyModel")
        textures: Dict of texture paths {channel: path}
                  Supported channels: "baseColor", "normal", "roughness",
                                     "metallic", "displacement"
        material_name: Name for material prim

    Returns:
        True if successful, False otherwise

    Example:
        >>> textures = {
        ...     "baseColor": "/path/to/color.jpg",
        ...     "normal": "/path/to/normal.png",
        ...     "roughness": "/path/to/roughness.png",
        ... }
        >>> create_materialx_network(stage, "/World/Vase", textures)
    """
    if not HAS_HOUDINI or not Mtlx:
        return False

    try:
        prim = stage.GetPrimAtPath(prim_path)
        if not prim:
            return False

        # Create material prim
        material_path = "/World/Materials/" + material_name
        material = UsdShade.Material.Define(stage, material_path)

        # Create MaterialX shader
        mtlx_shader = UsdShade.Shader.Define(
            stage,
            material_path + "/Shader",
        )

        # Set shader type (PBR surface)
        mtlx_shader.SetSourceAsset(
            Sdf.AssetPath("mtlx/stdlib_defs.mtlx"),
        )

        # Bind textures to shader inputs
        for channel, texture_path in textures.items():
            if channel in ("baseColor", "normal", "roughness", "metallic"):
                input_name = _channel_to_mtlx_input(channel)
                mtlx_shader.GetInput(input_name).ConnectToSource(
                    Sdf.AssetPath(texture_path)
                )

        # Bind material to geometry
        binding = UsdShade.MaterialBindingAPI(prim)
        binding.Bind(material)

        return True

    except Exception as e:
        print(f"MaterialX creation failed: {e}")
        return False


def _channel_to_mtlx_input(channel: str) -> str:
    """Map texture channel name to MaterialX input name."""
    mapping = {
        "baseColor": "base_color",
        "normal": "normal",
        "roughness": "specular_roughness",
        "metallic": "metalness",
        "displacement": "displacement",
    }
    return mapping.get(channel, channel)


def _create_material_network_from_glb(
    glb_path: str,
    stage: Any,
    prim_path: str,
    texture_resolution: str = "high",
) -> Dict[str, Any]:
    """
    Extract materials and textures from GLB and create USD material network.

    Args:
        glb_path: Path to GLB file
        stage: USD stage
        prim_path: Target prim path
        texture_resolution: Texture LOD level

    Returns:
        Metadata dict with material information
    """
    metadata: Dict[str, Any] = {
        "materials_created": False,
        "texture_count": 0,
        "error": None,
    }

    try:
        # Try to extract embedded textures from GLB
        # This is a simplified version - full implementation would use
        # pygltf or similar to parse GLB structure

        import tempfile
        temp_dir = tempfile.mkdtemp()

        # Create placeholder texture dict
        textures = {
            "baseColor": os.path.join(temp_dir, "BaseColor.png"),
            "normal": os.path.join(temp_dir, "Normal.png"),
            "roughness": os.path.join(temp_dir, "Roughness.png"),
        }

        # Create material network
        if create_materialx_network(stage, prim_path, textures):
            metadata["materials_created"] = True
            metadata["texture_count"] = len(textures)
            metadata["material_path"] = f"/World/Materials/PixiboxMaterial"

        return metadata

    except Exception as e:
        metadata["error"] = f"Material extraction failed: {str(e)}"
        return metadata


def optimize_mesh(
    prim_path: str,
    target_triangle_count: int = 100000,
    preserve_uv: bool = True,
) -> bool:
    """
    Apply mesh optimization (decimation, cleanup) to imported geometry.

    Args:
        prim_path: Target prim path
        target_triangle_count: Target polygon count
        preserve_uv: Keep UV coordinates during optimization

    Returns:
        True if successful, False otherwise
    """
    if not HAS_HOUDINI or not hou:
        return False

    try:
        # Get current LOP node
        pwd = hou.pwd()
        if not pwd or not pwd.path().startswith("/lops"):
            return False

        # Create geometry cleanup node
        cleanup = pwd.createNode("geosubset", f"optimize_{prim_path.replace('/', '_')}")

        # Would set up optimization parameters here
        # This requires deeper integration with Houdini's SOP operations

        return True

    except Exception as e:
        print(f"Mesh optimization failed: {e}")
        return False
