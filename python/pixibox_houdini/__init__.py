"""Pixibox AI plugin for Houdini.

This module provides integration with Houdini for AI-powered 3D generation,
USD/Solaris support, and Live Bridge real-time sync.
"""

__version__ = "2.1.0"
__author__ = "Pixibox.ai"
__license__ = "Commercial"

try:
    import hou
    HOUDINI_AVAILABLE = True
except ImportError:
    HOUDINI_AVAILABLE = False

# Import submodules
if HOUDINI_AVAILABLE:
    try:
        from . import api
        from . import hda_node
        from . import shelf_tools
        from . import menu
        from . import lop_utils
        from . import bridge
    except ImportError as e:
        print(f"Warning: Could not import Pixibox modules: {e}")

    # Cleanup on unload
    def _cleanup():
        """Clean up resources on plugin unload."""
        try:
            from . import bridge
            bridge.stop_live_bridge()
        except Exception:
            pass

__all__ = [
    "api",
    "hda_node",
    "shelf_tools",
    "menu",
    "lop_utils",
    "bridge",
]
