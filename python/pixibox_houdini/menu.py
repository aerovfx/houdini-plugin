"""Pixibox menu integration for Houdini."""

import hou
from . import shelf_tools
from . import bridge


def open_dashboard():
    """Open Pixibox dashboard in browser."""
    import webbrowser
    webbrowser.open("https://pixibox.ai/dashboard")


def open_docs():
    """Open Pixibox Houdini documentation."""
    import webbrowser
    webbrowser.open("https://pixibox.ai/docs/houdini")


def create_pixibox_menu():
    """Create Pixibox menu in Houdini main menu.

    Returns:
        XML menu definition string
    """
    menu_script = """
    <menuItem id="pixibox_ai">
        <label>Pixibox AI</label>
        <scriptItem id="pixibox_generate_text">
            <label>Generate from Text</label>
            <scriptCode>
                import sys
                sys.path.insert(0, hou.expandString('$HOUDINI_USER_DIR/python_panels'))
                from pixibox_shelf import show_generate_dialog
                show_generate_dialog()
            </scriptCode>
        </scriptItem>
        <separatorItem/>
        <scriptItem id="pixibox_create_node">
            <label>Create Pixibox SOP</label>
            <scriptCode>
                import sys
                sys.path.insert(0, hou.expandString('$HOUDINI_USER_DIR/python_panels'))
                from pixibox_shelf import create_pixibox_node
                create_pixibox_node()
            </scriptCode>
        </scriptItem>
        <separatorItem/>
        <scriptItem id="pixibox_import_usd">
            <label>Import USD...</label>
            <scriptCode>
                import sys
                sys.path.insert(0, hou.expandString('$HOUDINI_USER_DIR/python_panels'))
                from pixibox_shelf import import_usd_dialog
                import_usd_dialog()
            </scriptCode>
        </scriptItem>
        <scriptItem id="pixibox_browse_scenes">
            <label>Browse Scenes...</label>
            <scriptCode>
                import sys
                sys.path.insert(0, hou.expandString('$HOUDINI_USER_DIR/python_panels'))
                from pixibox_shelf import browse_scenes_dialog
                browse_scenes_dialog()
            </scriptCode>
        </scriptItem>
        <separatorItem/>
        <scriptItem id="pixibox_live_bridge">
            <label>Toggle Live Bridge</label>
            <scriptCode>
                import sys
                sys.path.insert(0, hou.expandString('$HOUDINI_USER_DIR/python_panels'))
                from pixibox_shelf import toggle_live_bridge
                toggle_live_bridge()
            </scriptCode>
        </scriptItem>
        <separatorItem/>
        <scriptItem id="pixibox_dashboard">
            <label>Open Dashboard</label>
            <scriptCode>
                import webbrowser
                webbrowser.open('https://pixibox.ai/dashboard')
            </scriptCode>
        </scriptItem>
        <scriptItem id="pixibox_docs">
            <label>Documentation</label>
            <scriptCode>
                import webbrowser
                webbrowser.open('https://pixibox.ai/docs/houdini')
            </scriptCode>
        </scriptItem>
    </menuItem>
    """

    return menu_script


def install_menu_integration():
    """Install menu items programmatically.

    Note: Houdini requires menu items to be defined in MainMenuCommon.xml
    rather than created dynamically. Use create_pixibox_menu() output in your
    MainMenuCommon.xml file instead.
    """
    try:
        hou.ui.displayMessage(
            "Pixibox menu integration requires adding menu items to MainMenuCommon.xml.\n\n"
            "Copy the menu definition from create_pixibox_menu() and add it to:\n"
            "$HOUDINI_USER_DIR/config/MainMenuCommon.xml",
            severity=hou.severityType.Message
        )
    except Exception as e:
        hou.ui.displayMessage(
            f"Error installing menu: {str(e)}",
            severity=hou.severityType.Error
        )


def register_usd_import_callback():
    """Register callback for USD import from Live Bridge.

    This callback handles generation_complete events from the bridge
    and updates the UI accordingly.
    """
    try:
        live_bridge = bridge.get_live_bridge()
        if not live_bridge:
            return

        def on_generation(data):
            """Handle generation complete event.

            Args:
                data: Generation data from bridge
            """
            gen_id = data.get("id")
            scene_name = data.get("name", "Untitled")

            hou.ui.setStatusMessage(
                f"Pixibox: New generation available: {scene_name}",
                severity=hou.severityType.Message
            )

        live_bridge.on("generation_complete", on_generation)

    except Exception as e:
        hou.ui.setStatusMessage(
            f"Failed to register Live Bridge callback: {str(e)}",
            severity=hou.severityType.Warning
        )
