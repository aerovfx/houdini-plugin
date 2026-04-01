"""
Shelf tool implementations for Pixibox Houdini plugin.

Provides user-facing functions that are called from shelf buttons and menus.
"""

import os
from typing import Optional, Dict, Any

try:
    import hou
    from hou import ui
    HAS_HOUDINI = True
except ImportError:
    HAS_HOUDINI = False
    hou = None  # type: ignore
    ui = None  # type: ignore


from .api import PixiboxClient, get_generation
from .bridge import PixiboxBridge
from .lop_utils import import_to_stage


class PixiboxSettingsDialog:
    """Settings dialog for Pixibox configuration."""

    def show(self) -> Optional[Dict[str, str]]:
        """
        Show settings dialog and return updated config.

        Returns:
            Dict with settings or None if cancelled
        """
        if not HAS_HOUDINI:
            print("Error: Houdini not available")
            return None

        # Create dialog
        dialog = ui.Qt.QDialog(hou.qt.mainWindow())
        dialog.setWindowTitle("Pixibox Settings")
        dialog.setMinimumWidth(500)

        # Layout
        layout = ui.Qt.QVBoxLayout()

        # API Endpoint
        api_label = ui.Qt.QLabel("API Endpoint:")
        api_input = ui.Qt.QLineEdit()
        api_input.setText(
            os.getenv("PIXIBOX_API_ENDPOINT", "https://pixibox.ai/api")
        )
        layout.addWidget(api_label)
        layout.addWidget(api_input)

        # Auth Token
        token_label = ui.Qt.QLabel("Auth Token:")
        token_input = ui.Qt.QLineEdit()
        token_input.setEchoMode(ui.Qt.QLineEdit.Password)
        token_input.setText(os.getenv("PIXIBOX_AUTH_TOKEN", ""))
        layout.addWidget(token_label)
        layout.addWidget(token_input)

        # Default Model
        model_label = ui.Qt.QLabel("Default Model:")
        model_combo = ui.Qt.QComboBox()
        model_combo.addItems([
            "nvidia-edify",
            "hunyuan-3d",
            "fal-gltf-generator",
            "fal-text-to-3d",
        ])
        current_model = os.getenv("PIXIBOX_DEFAULT_MODEL", "nvidia-edify")
        model_combo.setCurrentText(current_model)
        layout.addWidget(model_label)
        layout.addWidget(model_combo)

        # Auto-import checkbox
        auto_import_check = ui.Qt.QCheckBox("Auto-import completed generations")
        auto_import_check.setChecked(
            os.getenv("PIXIBOX_AUTO_IMPORT", "1") == "1"
        )
        layout.addWidget(auto_import_check)

        # Material options group
        mat_group = ui.Qt.QGroupBox("Material Options")
        mat_layout = ui.Qt.QVBoxLayout()

        mtlx_check = ui.Qt.QCheckBox("Apply MaterialX materials")
        mtlx_check.setChecked(
            os.getenv("PIXIBOX_USE_MATERIALX", "1") == "1"
        )
        mat_layout.addWidget(mtlx_check)

        tex_res_label = ui.Qt.QLabel("Texture Resolution:")
        tex_res_combo = ui.Qt.QComboBox()
        tex_res_combo.addItems(["low", "medium", "high"])
        current_res = os.getenv("PIXIBOX_TEXTURE_RESOLUTION", "high")
        tex_res_combo.setCurrentText(current_res)
        mat_layout.addWidget(tex_res_label)
        mat_layout.addWidget(tex_res_combo)

        mat_group.setLayout(mat_layout)
        layout.addWidget(mat_group)

        # Buttons
        button_layout = ui.Qt.QHBoxLayout()
        ok_button = ui.Qt.QPushButton("OK")
        cancel_button = ui.Qt.QPushButton("Cancel")

        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        if dialog.exec():
            return {
                "api_endpoint": api_input.text(),
                "auth_token": token_input.text(),
                "default_model": model_combo.currentText(),
                "auto_import": "1" if auto_import_check.isChecked() else "0",
                "use_materialx": "1" if mtlx_check.isChecked() else "0",
                "texture_resolution": tex_res_combo.currentText(),
            }

        return None


def generate_from_prompt() -> None:
    """Open dialog to generate 3D model from text prompt."""

    if not HAS_HOUDINI:
        print("Error: Houdini not available")
        return

    # Create dialog
    dialog = ui.Qt.QDialog(hou.qt.mainWindow())
    dialog.setWindowTitle("Generate from Prompt")
    dialog.setMinimumWidth(600)

    layout = ui.Qt.QVBoxLayout()

    # Model selection
    model_label = ui.Qt.QLabel("AI Model:")
    model_combo = ui.Qt.QComboBox()
    model_combo.addItems([
        "nvidia-edify",
        "hunyuan-3d",
        "fal-gltf-generator",
        "fal-text-to-3d",
    ])
    default_model = os.getenv("PIXIBOX_DEFAULT_MODEL", "nvidia-edify")
    model_combo.setCurrentText(default_model)
    layout.addWidget(model_label)
    layout.addWidget(model_combo)

    # Prompt input
    prompt_label = ui.Qt.QLabel("Prompt:")
    prompt_input = ui.Qt.QTextEdit()
    prompt_input.setPlaceholderText(
        "Describe the 3D model you want to generate...\n"
        "Example: A ceramic vase with intricate geometric patterns"
    )
    prompt_input.setMinimumHeight(120)
    layout.addWidget(prompt_label)
    layout.addWidget(prompt_input)

    # Status label
    status_label = ui.Qt.QLabel("")
    status_label.setStyleSheet("color: gray; font-style: italic;")
    layout.addWidget(status_label)

    # Buttons
    button_layout = ui.Qt.QHBoxLayout()
    generate_button = ui.Qt.QPushButton("Generate")
    cancel_button = ui.Qt.QPushButton("Cancel")

    def on_generate() -> None:
        prompt = prompt_input.toPlainText().strip()
        if not prompt:
            status_label.setText("Error: Please enter a prompt")
            return

        model = model_combo.currentText()
        status_label.setText("Generating... please wait")
        dialog.setEnabled(False)

        try:
            # Generate model
            from .api import generate
            gen_id = generate(
                mode="text-to-3d",
                prompt=prompt,
                model=model,
            )

            status_label.setText(f"Generation started: {gen_id}")

            # Show bridge panel for monitoring
            toggle_bridge()

            dialog.accept()

        except Exception as e:
            status_label.setText(f"Error: {str(e)}")
            dialog.setEnabled(True)

    generate_button.clicked.connect(on_generate)
    cancel_button.clicked.connect(dialog.reject)

    button_layout.addStretch()
    button_layout.addWidget(generate_button)
    button_layout.addWidget(cancel_button)
    layout.addLayout(button_layout)

    dialog.setLayout(layout)
    dialog.exec()


def generate_from_image() -> None:
    """Open dialog to generate 3D model from image."""

    if not HAS_HOUDINI:
        print("Error: Houdini not available")
        return

    # File picker
    file_dialog = ui.Qt.QFileDialog()
    file_dialog.setFileMode(ui.Qt.QFileDialog.ExistingFile)
    file_dialog.setNameFilter("Images (*.jpg *.jpeg *.png *.tiff *.tif)")
    file_dialog.setWindowTitle("Select Image for 3D Generation")

    if not file_dialog.exec():
        return

    image_path = file_dialog.selectedFiles()[0]

    # Model selection dialog
    dialog = ui.Qt.QDialog(hou.qt.mainWindow())
    dialog.setWindowTitle("Generate from Image")
    dialog.setMinimumWidth(500)

    layout = ui.Qt.QVBoxLayout()

    # Show selected image
    image_label = ui.Qt.QLabel(f"Image: {image_path}")
    image_label.setStyleSheet("color: gray;")
    layout.addWidget(image_label)

    # Model selection
    model_label = ui.Qt.QLabel("AI Model:")
    model_combo = ui.Qt.QComboBox()
    model_combo.addItems([
        "nvidia-edify",
        "hunyuan-3d",
        "fal-gltf-generator",
    ])
    layout.addWidget(model_label)
    layout.addWidget(model_combo)

    # Optional prompt refinement
    refine_label = ui.Qt.QLabel("Refinement Prompt (optional):")
    refine_input = ui.Qt.QLineEdit()
    refine_input.setPlaceholderText("Describe changes to the generated model...")
    layout.addWidget(refine_label)
    layout.addWidget(refine_input)

    # Status label
    status_label = ui.Qt.QLabel("")
    status_label.setStyleSheet("color: gray; font-style: italic;")
    layout.addWidget(status_label)

    # Buttons
    button_layout = ui.Qt.QHBoxLayout()
    generate_button = ui.Qt.QPushButton("Generate")
    cancel_button = ui.Qt.QPushButton("Cancel")

    def on_generate() -> None:
        model = model_combo.currentText()
        status_label.setText("Generating... please wait")
        dialog.setEnabled(False)

        try:
            from .api import generate
            gen_id = generate(
                mode="image-to-3d",
                image_path=image_path,
                model=model,
            )

            status_label.setText(f"Generation started: {gen_id}")
            toggle_bridge()
            dialog.accept()

        except Exception as e:
            status_label.setText(f"Error: {str(e)}")
            dialog.setEnabled(True)

    generate_button.clicked.connect(on_generate)
    cancel_button.clicked.connect(dialog.reject)

    button_layout.addStretch()
    button_layout.addWidget(generate_button)
    button_layout.addWidget(cancel_button)
    layout.addLayout(button_layout)

    dialog.setLayout(layout)
    dialog.exec()


def import_latest() -> None:
    """Import the most recent generation to USD stage."""

    if not HAS_HOUDINI:
        print("Error: Houdini not available")
        return

    try:
        from .api import list_generations

        # Get latest generation
        generations = list_generations(limit=1)
        if not generations:
            print("No generations found")
            return

        latest = generations[0]
        gen_id = latest["id"]

        # Check status
        gen_status = get_generation(gen_id)
        if gen_status["status"] != "completed":
            print(f"Generation not completed: {gen_status['status']}")
            return

        # Import to stage
        node_path, metadata = import_to_stage(
            gen_id,
            apply_materialx=os.getenv("PIXIBOX_USE_MATERIALX", "1") == "1",
        )

        if node_path:
            print(f"Imported to {node_path}")
            print(f"Metadata: {metadata}")
        else:
            print(f"Import failed: {metadata.get('error')}")

    except Exception as e:
        print(f"Error importing latest: {str(e)}")


def toggle_bridge() -> None:
    """Toggle Pixibox Bridge real-time update panel."""

    if not HAS_HOUDINI:
        print("Error: Houdini not available")
        return

    print("Toggling Pixibox Bridge...")

    try:
        bridge = PixiboxBridge()

        if bridge.is_connected():
            bridge.disconnect()
            print("Pixibox Bridge disconnected")
        else:
            bridge.connect()

            def on_update(gen: Dict[str, Any]) -> None:
                status = gen.get("status", "unknown")
                progress = gen.get("progress", 0)
                print(f"[{gen['id']}] {status} ({progress}%)")

            bridge.on_generation_update(on_update)
            print("Pixibox Bridge connected")

    except Exception as e:
        print(f"Error toggling bridge: {str(e)}")


def open_settings() -> None:
    """Open Pixibox settings dialog."""

    if not HAS_HOUDINI:
        print("Error: Houdini not available")
        return

    dialog = PixiboxSettingsDialog()
    settings = dialog.show()

    if settings:
        # Save to environment or config file
        for key, value in settings.items():
            env_key = f"PIXIBOX_{key.upper()}"
            os.environ[env_key] = value
        print("Settings updated")
