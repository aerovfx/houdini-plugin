"""
Houdini startup script for Pixibox plugin.

This script runs automatically when Houdini launches if the plugin is installed.
Handles initialization, environment setup, and toolbar registration.
"""

import os
import sys

try:
    import hou
except ImportError:
    # Not in Houdini context
    sys.exit(0)


def setup_pixibox_environment() -> None:
    """
    Initialize Pixibox environment variables and paths.

    Runs on Houdini startup to configure plugin.
    """
    plugin_root = os.getenv("PIXIBOX_HOUDINI", "")

    if not plugin_root:
        # Try to find plugin from HOUDINI_PACKAGE_PATH
        package_path = os.getenv("HOUDINI_PACKAGE_PATH", "")
        if package_path:
            plugin_root = os.path.join(package_path, "pixibox")

    if not plugin_root or not os.path.exists(plugin_root):
        print("[Pixibox] Warning: Could not locate plugin directory")
        return

    # Set up Python path for imports
    python_path = os.path.join(plugin_root, "python")
    if python_path not in sys.path:
        sys.path.insert(0, python_path)

    # Set default environment variables if not already set
    defaults = {
        "PIXIBOX_API_ENDPOINT": "https://pixibox.ai/api",
        "PIXIBOX_WEBSOCKET_ENDPOINT": "wss://pixibox.ai/ws",
        "PIXIBOX_DEFAULT_MODEL": "nvidia-edify",
        "PIXIBOX_AUTO_IMPORT": "1",
        "PIXIBOX_USE_MATERIALX": "1",
        "PIXIBOX_TEXTURE_RESOLUTION": "high",
        "PIXIBOX_TIMEOUT": "300",
        "PIXIBOX_DEBUG": "0",
    }

    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value

    print(f"[Pixibox] Plugin initialized from {plugin_root}")


def register_pixibox_tools() -> None:
    """
    Register Pixibox shelf tools and menu items.

    Called during Houdini startup.
    """
    try:
        plugin_root = os.getenv("PIXIBOX_HOUDINI", "")
        shelf_path = os.path.join(plugin_root, "toolbar", "pixibox.shelf")

        if os.path.exists(shelf_path):
            # Shelf will be auto-loaded by Houdini
            print("[Pixibox] Shelf tools registered")
        else:
            print(f"[Pixibox] Warning: Shelf not found at {shelf_path}")

    except Exception as e:
        print(f"[Pixibox] Error registering tools: {e}")


def verify_dependencies() -> None:
    """
    Check for required dependencies.

    Warns if critical packages are missing.
    """
    missing = []

    # Check websocket-client
    try:
        import websocket  # noqa: F401
    except ImportError:
        missing.append("websocket-client")

    # Check for USD libraries (should be in Houdini)
    try:
        from pxr import Usd  # noqa: F401
    except ImportError:
        print("[Pixibox] Warning: USD libraries not available (Solaris features disabled)")

    if missing:
        print(f"[Pixibox] Warning: Missing packages: {', '.join(missing)}")
        print("[Pixibox] Install via: pip install " + " ".join(missing))


def create_pixibox_menu() -> None:
    """
    Create Pixibox menu in Houdini's menu bar.

    Adds quick access to generation and settings.
    """
    try:
        # Menu items would be defined here
        # This is a placeholder for future menu integration
        pass

    except Exception as e:
        print(f"[Pixibox] Error creating menu: {e}")


def main() -> None:
    """Main initialization entry point."""
    try:
        # Set up environment
        setup_pixibox_environment()

        # Verify dependencies
        verify_dependencies()

        # Register tools
        register_pixibox_tools()

        # Create menu (if needed)
        create_pixibox_menu()

        print("[Pixibox] Plugin loaded successfully")

    except Exception as e:
        print(f"[Pixibox] Fatal error during initialization: {e}")
        import traceback
        traceback.print_exc()


# Run initialization on Houdini startup
if __name__ == "__main__":
    main()
else:
    # Also run if imported as module
    main()
