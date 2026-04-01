# Pixibox Houdini Plugin

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Houdini 19.5+](https://img.shields.io/badge/Houdini-19.5%2B-orange.svg)](https://www.sidefx.com)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org)

Deep Solaris/LOP integration for [Pixibox.ai](https://pixibox.ai) — the 3D AI tool comparison platform. Generate 3D models from prompts or images directly within Houdini, with real-time syncing, USD composition, and automatic MaterialX conversion.

## Features

- **Prompt-to-3D & Image-to-3D** — Generate 3D models using multiple AI providers (NVIDIA Edify, Tencent Hunyuan, Fal.ai, etc.)
- **Native Solaris Integration** — Import directly to USD stage with proper LOPs node setup
- **MaterialX Conversion** — Automatic material network generation with PBR textures
- **Live Bridge** — WebSocket real-time sync between Pixibox platform and Houdini
- **Shelf Tools** — Quick-access generation and import buttons
- **Multi-Format Support** — GLB, GLTF, OBJ with intelligent loader
- **Typed Python API** — Full type hints for IDE autocomplete
- **History & Management** — Browse, organize, and import past generations
- **Settings Panel** — Configure API endpoint, authentication, and preferences

## Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| Houdini | 19.5+ | Solaris/LOP license required for USD composition |
| Python | 3.9+ | Built-in with Houdini |
| Solaris License | ✓ | Required for LOPs node-based composition |
| Internet | ✓ | Real-time API communication with Pixibox.ai |

## Installation

### Option 1: Houdini Package Manager (Recommended)

1. Open Houdini and go to **Help → Package Manager**
2. Click **+ Add Package**
3. Select the `pixibox.json` file from this plugin
4. Restart Houdini

### Option 2: Manual Installation

1. Locate your Houdini packages directory:
   - **Linux/Mac**: `$HOME/houdini19.5/packages/`
   - **Windows**: `%APPDATA%\Houdini\19.5\packages\`

2. Copy this entire `houdini-plugin` folder to `packages/pixibox/`

3. Create or edit `packages/pixibox.json`:
   ```json
   {
     "env": [{"PIXIBOX_HOUDINI": "$HOUDINI_PACKAGE_PATH/pixibox"}],
     "path": "$PIXIBOX_HOUDINI"
   }
   ```

4. Restart Houdini

### Option 3: Development Setup

```bash
# Clone the plugin into your packages directory
cd ~/houdini19.5/packages/
git clone https://github.com/pixibox-ai/houdini-plugin pixibox

# Verify installation
houdini
# Should show "Pixibox" shelf in toolbar
```

## Quick Start

### Generate from Prompt

1. Go to **Solaris** tab
2. Click **Pixibox → Generate from Prompt** on the shelf
3. Enter your prompt: *"A ceramic vase with intricate patterns"*
4. Select AI model and click **Generate**
5. Watch real-time progress in the Pixibox Bridge panel
6. Auto-imports to USD stage when complete

### Generate from Image

1. Click **Pixibox → Generate from Image** on the shelf
2. Select an image file (JPEG, PNG, TIFF)
3. Choose model and click **Generate**
4. Monitor in Bridge panel
5. Auto-imports with textures applied

### Import Previous Generation

1. Click **Pixibox → Import Latest** on the shelf
2. Or use **Pixibox → History** to browse all past generations
3. Select the generation and click **Import**
4. Choose target prim path and options:
   - Apply MaterialX materials
   - Auto-optimize mesh
   - Set shader LOD

## Configuration

### Settings Panel

1. Click **Pixibox → Settings** on the shelf
2. Configure:
   - **API Endpoint**: Default is `https://pixibox.ai/api` (or your self-hosted instance)
   - **Auth Token**: Your Pixibox API token (get from account settings)
   - **Default Model**: Preferred AI provider for generations
   - **Auto-Import**: Automatically import generations to stage
   - **Material Options**: PBR setup, texture resolution, etc.

### Environment Variables

Set in your `houdini.env`:

```
# Pixibox API Configuration
PIXIBOX_API_ENDPOINT=https://pixibox.ai/api
PIXIBOX_AUTH_TOKEN=your-api-token-here
PIXIBOX_DEFAULT_MODEL=nvidia-edify

# Advanced
PIXIBOX_TIMEOUT=300
PIXIBOX_DEBUG=0
```

## API Usage

### Python API

```python
from pixibox_houdini import generate, import_to_stage, get_generation
from pixibox_houdini.bridge import PixiboxBridge

# Generate from prompt
generation_id = generate(
    mode="text-to-3d",
    prompt="A sleek modern chair",
    model="nvidia-edify"
)
print(f"Generation {generation_id} started")

# Import to current stage
import_to_stage(
    generation_id=generation_id,
    prim_path="/World/Imports/MyChair",
    apply_materialx=True
)

# Watch live updates
bridge = PixiboxBridge()
bridge.connect()
bridge.on_generation_update(
    lambda gen: print(f"Status: {gen['status']}")
)
bridge.wait()
```

### REST Endpoints

Use the embedded API client for direct REST calls:

```python
from pixibox_houdini.api import PixiboxClient

client = PixiboxClient(
    endpoint="https://pixibox.ai/api",
    token="your-token"
)

# List generations
gens = client.list_generations(limit=10, skip=0)

# Download specific format
client.download_model(
    generation_id="gen-123",
    format="glb",  # glb, gltf, obj
    output_path="/tmp/model.glb"
)
```

## Shelf Tools Reference

| Tool | Function | Shortcut |
|------|----------|----------|
| **Generate from Prompt** | Open text-to-3D dialog | `P` (in Solaris) |
| **Generate from Image** | Open image-to-3D dialog | `I` (in Solaris) |
| **Import Latest** | Auto-import last generation | ⌘+I / Ctrl+I |
| **Toggle Bridge** | Show/hide live sync panel | `B` (in Solaris) |
| **Settings** | Open configuration panel | `⌘+, / Ctrl+,` |
| **History** | Browse past generations | `H` (in Solaris) |

## HDAs (Houdini Digital Assets)

### `Pixibox_Generate` HDA

Custom node for batch generation directly in SOPs:

```python
# In SOPs network, dive into Pixibox_Generate node
# Configure:
# - Prompt/Image input
# - Model selection
# - Batch count & options
# - Auto-import trigger

# Node outputs:
# Output 1: Generated geometry (packed)
# Output 2: Material assignment details
# Output 3: Metadata (generation_id, timing, etc)
```

**Compilation**: HDA must be compiled in Houdini Desktop:
1. **File → Save as Digital Asset...**
2. Set name to `Pixibox_Generate`
3. Save to `otls/pixibox_generate.hda`

## Troubleshooting

### Connection Issues

```
Error: Failed to connect to Pixibox API
```

**Solution**:
- Check `PIXIBOX_API_ENDPOINT` environment variable
- Verify API token in settings (not expired)
- Check firewall/proxy settings
- Test: `python -c "from pixibox_houdini.api import PixiboxClient; PixiboxClient().health_check()"`

### Import Fails to Solaris

```
Error: Failed to import to USD stage
```

**Solution**:
- Ensure **Solaris license** is active
- Check you're in **LOPs/Solaris tab**
- Verify prim path is valid (e.g., `/World/Imports/MyAsset`)
- Try manual import: **Solaris → Import USD → Select GLB file**

### Mesh Has Issues

```
Model appears broken or wrong after import
```

**Solution**:
- Enable **Auto-Optimize Mesh** in settings
- Try different material LOD (low/medium/high)
- Check generation status is **complete** (not failed)
- Re-import and apply **MaterialX conversion** checkbox

### Python Errors

```
ModuleNotFoundError: No module named 'pixibox_houdini'
```

**Solution**:
- Verify plugin installed correctly (check `$PIXIBOX_HOUDINI` environment variable)
- Restart Houdini after installation
- Check `python/pixibox_houdini/` folder exists in plugin directory

## Development

### Project Structure

```
houdini-plugin/
├── README.md
├── LICENSE
├── pixibox.json                      # Houdini package descriptor
├── python/
│   └── pixibox_houdini/
│       ├── __init__.py               # Public API
│       ├── api.py                    # REST client
│       ├── bridge.py                 # WebSocket real-time sync
│       ├── lop_utils.py              # Solaris/LOPs utilities
│       └── shelf_tools.py            # Shelf tool entry points
├── toolbar/
│   └── pixibox.shelf                 # Houdini shelf XML
├── otls/
│   └── pixibox_generate.hda          # Custom HDA (compiled in Houdini)
└── scripts/
    └── OnCreated.py                  # Houdini startup script
```

### Building from Source

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Type-check code
mypy python/

# Lint
ruff check python/
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Write typed code (Python 3.9+)
4. Add tests for new functionality
5. Submit a pull request

## Changelog

### v1.0.0 (2026-04-01)

- Initial release
- Prompt-to-3D and Image-to-3D generation
- Solaris/LOPs integration with USD composition
- MaterialX material conversion
- Live WebSocket bridge for real-time updates
- Shelf tools and settings panel
- Full typed Python API

## License

MIT License — see [LICENSE](LICENSE) file for details.

Copyright (c) 2026 Pixibox.ai

## Support

- **Documentation**: [docs.pixibox.ai/houdini](https://docs.pixibox.ai/houdini)
- **Issues**: [GitHub Issues](https://github.com/pixibox-ai/houdini-plugin/issues)
- **Community**: [Discord](https://discord.gg/pixibox)
- **Email**: support@pixibox.ai

## Acknowledgments

Built with ❤️ by the Pixibox team. Special thanks to SideFX for the Houdini platform and the Solaris community.
