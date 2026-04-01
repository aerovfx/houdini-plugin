# Pixibox Houdini Plugin — Quick Index

## Start Here

1. **New User?** Read [README.md](README.md) — Installation, quick start, features, troubleshooting
2. **Developer?** Read [CONTRIBUTING.md](CONTRIBUTING.md) — Development setup, code style, testing
3. **Architect?** Read [PLUGIN_ARCHITECTURE.md](PLUGIN_ARCHITECTURE.md) — Design, modules, extension points
4. **Inventory?** Read [PROJECT_MANIFEST.md](PROJECT_MANIFEST.md) — Files, stats, feature list

## File Guide

### Documentation

| File | Audience | Focus |
|------|----------|-------|
| [README.md](README.md) | Users | Installation, features, usage examples |
| [PLUGIN_ARCHITECTURE.md](PLUGIN_ARCHITECTURE.md) | Developers | Technical design, module responsibilities |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributors | Code style, testing, git workflow |
| [PROJECT_MANIFEST.md](PROJECT_MANIFEST.md) | Project Leads | Inventory, stats, release notes |
| [INDEX.md](INDEX.md) | Everyone | This file — navigation guide |

### Python Modules

| File | Purpose | Audience |
|------|---------|----------|
| [python/pixibox_houdini/__init__.py](python/pixibox_houdini/__init__.py) | Public API | Users & developers |
| [python/pixibox_houdini/api.py](python/pixibox_houdini/api.py) | REST client | Developers |
| [python/pixibox_houdini/bridge.py](python/pixibox_houdini/bridge.py) | WebSocket | Developers |
| [python/pixibox_houdini/lop_utils.py](python/pixibox_houdini/lop_utils.py) | Solaris integration | Advanced users |
| [python/pixibox_houdini/shelf_tools.py](python/pixibox_houdini/shelf_tools.py) | UI dialogs | Developers |

### Configuration

| File | Purpose |
|------|---------|
| [pixibox.json](pixibox.json) | Houdini package descriptor |
| [.gitignore](.gitignore) | Git patterns |
| [LICENSE](LICENSE) | MIT license |

### Tools & Scripts

| File | Purpose |
|------|---------|
| [toolbar/pixibox.shelf](toolbar/pixibox.shelf) | Shelf definition (6 tools) |
| [scripts/OnCreated.py](scripts/OnCreated.py) | Houdini startup init |
| [otls/README.md](otls/README.md) | HDA compilation guide |

## Quick API Reference

### Import & Generate

```python
from pixibox_houdini import generate, import_to_stage

# Text-to-3D
gen_id = generate("text-to-3d", "A ceramic vase", "nvidia-edify")

# With import
import_to_stage(gen_id, "/World/Imports/Vase", apply_materialx=True)
```

### Real-time Monitoring

```python
from pixibox_houdini.bridge import PixiboxBridge

bridge = PixiboxBridge()
bridge.on_generation_update(lambda g: print(f"{g['status']}"))
bridge.connect()
result = bridge.wait(timeout=300)
```

### Advanced API

```python
from pixibox_houdini.api import PixiboxClient
from pixibox_houdini.lop_utils import get_current_stage, create_materialx_network

# List past generations
client = PixiboxClient(token="...")
gens = client.list_generations(limit=20)

# Work with USD stage
stage = get_current_stage()
create_materialx_network(stage, "/World/Model", textures)
```

## Environment Setup

```bash
# Set API token (required)
export PIXIBOX_AUTH_TOKEN="your-token-here"

# Optional: customize defaults
export PIXIBOX_API_ENDPOINT="https://pixibox.ai/api"
export PIXIBOX_DEFAULT_MODEL="nvidia-edify"
export PIXIBOX_AUTO_IMPORT="1"
export PIXIBOX_USE_MATERIALX="1"
```

## Installation

### Package Manager (Recommended)

1. Help → Package Manager
2. Add Package → Select pixibox.json
3. Restart Houdini

### Manual

```bash
cp -r houdini-plugin ~/houdini19.5/packages/pixibox
# Create pixibox.json in ~/.houdini19.5/packages/
```

## Shelf Tools

| Tool | Shortcut | Function |
|------|----------|----------|
| Generate from Prompt | P | Text-to-3D dialog |
| Generate from Image | I | Image-to-3D dialog |
| Import Latest | ⌘I | Auto-import most recent |
| Toggle Bridge | B | Connect/disconnect updates |
| Settings | ⌘, | Configuration panel |
| Help | — | Quick start guide |

## Common Tasks

### Generate a Model

1. Click **Generate from Prompt** shelf tool
2. Enter description (e.g., "A wooden chair")
3. Select AI model
4. Click **Generate**
5. Watch progress in Bridge panel
6. Auto-imports when complete

### Import to Stage

```python
from pixibox_houdini import import_to_stage

import_to_stage(
    generation_id="gen-123",
    prim_path="/World/Imports/MyAsset",
    apply_materialx=True,
)
```

### Configure Settings

1. Click **Settings** shelf tool
2. Set API token
3. Choose default AI model
4. Enable/disable MaterialX
5. Save changes

### Monitor Generation

```python
from pixibox_houdini.bridge import PixiboxBridge

bridge = PixiboxBridge()
bridge.connect()

def on_update(gen):
    print(f"{gen['id']}: {gen['status']} ({gen.get('progress', 0)}%)")

bridge.on_generation_update(on_update)
```

## Troubleshooting

### "Not in Solaris context"

- Switch to **Solaris** tab in viewport
- Ensure LOPs network is active
- Check Solaris license is valid

### "API authentication failed"

- Verify `PIXIBOX_AUTH_TOKEN` is set
- Check token has not expired
- Regenerate token at pixibox.ai account settings

### "WebSocket connection failed"

- Check internet connectivity
- Verify `PIXIBOX_WEBSOCKET_ENDPOINT` is correct
- Check firewall/proxy settings

### "Import fails to stage"

- Ensure you're in LOPs context
- Verify prim path is valid (e.g., `/World/Imports/Model`)
- Check generation status is "completed"
- Try manual import via Solaris menu

## Development Quick Start

```bash
# Clone to development directory
git clone https://github.com/pixibox-ai/houdini-plugin ~/dev/pixibox-houdini

# Set up environment
cd ~/dev/pixibox-houdini
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Type check
mypy python/pixibox_houdini

# Lint code
ruff check python/
black python/
```

## API Reference by Module

### pixibox_houdini (public API)

```python
generate()               # Create generation
get_generation()        # Get status
list_generations()      # Browse past
download_model()        # Download files
import_to_stage()       # Import to USD
create_materialx_network()  # Create materials
get_current_stage()     # Get USD stage
PixiboxClient          # REST API class
PixiboxBridge          # WebSocket class
```

### pixibox_houdini.api

```python
PixiboxClient:
  .generate()
  .get_generation()
  .list_generations()
  .download_model()
  .health_check()

Functions:
  generate()
  get_generation()
  list_generations()
  download_model()
```

### pixibox_houdini.bridge

```python
PixiboxBridge:
  .connect()
  .disconnect()
  .on_generation_update()
  .on_error()
  .on_connected()
  .wait()
  .is_connected()
```

### pixibox_houdini.lop_utils

```python
get_current_stage()
import_to_stage()
create_materialx_network()
optimize_mesh()
```

### pixibox_houdini.shelf_tools

```python
generate_from_prompt()
generate_from_image()
import_latest()
toggle_bridge()
open_settings()
```

## Version Info

- **Current Version**: 1.0.0
- **Release Date**: April 1, 2026
- **License**: MIT
- **Requires**: Houdini 19.5+, Python 3.9+

## Links

- **Documentation**: https://docs.pixibox.ai/houdini
- **GitHub**: https://github.com/pixibox-ai/houdini-plugin
- **Issues**: https://github.com/pixibox-ai/houdini-plugin/issues
- **Discord**: https://discord.gg/pixibox
- **Email**: support@pixibox.ai

## Getting Help

1. Check [README.md](README.md) troubleshooting section
2. Search [GitHub Issues](https://github.com/pixibox-ai/houdini-plugin/issues)
3. Ask in [Discord Community](https://discord.gg/pixibox)
4. Email support@pixibox.ai

---

**Last Updated**: 2026-04-01
**Maintained By**: Pixibox Team
