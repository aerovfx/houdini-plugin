# Pixibox Houdini Plugin — Architecture

## Overview

The Pixibox Houdini plugin provides deep integration with Houdini's Solaris (USD) environment, enabling 3D AI model generation directly within the DCC. The architecture emphasizes thread safety, type safety, and seamless Houdini integration.

## Directory Structure

```
houdini-plugin/
├── README.md                          # User documentation & quick start
├── PLUGIN_ARCHITECTURE.md             # This file
├── LICENSE                            # MIT license
├── .gitignore                         # Git ignore rules
├── pixibox.json                       # Houdini package descriptor
│
├── python/
│   └── pixibox_houdini/
│       ├── __init__.py               # Public API exports
│       ├── api.py                    # REST client (PixiboxClient, generate, etc)
│       ├── bridge.py                 # WebSocket bridge (real-time updates)
│       ├── lop_utils.py              # Solaris/LOPs utilities (USD, MaterialX)
│       └── shelf_tools.py            # Shelf tool implementations (dialogs, handlers)
│
├── toolbar/
│   └── pixibox.shelf                 # Houdini shelf XML definition
│
├── otls/
│   └── README.md                     # HDA compilation guide
│       # (Compiled .hda files go here)
│
└── scripts/
    └── OnCreated.py                  # Houdini startup initialization
```

## Module Responsibilities

### api.py — REST API Client

**Purpose**: HTTP communication with Pixibox backend

**Key Classes**:
- `PixiboxClient`: Main API client with methods:
  - `generate()`: Start text/image-to-3D generation
  - `get_generation()`: Poll generation status
  - `list_generations()`: Browse past generations
  - `download_model()`: Fetch completed models
  - `health_check()`: Test API connectivity

**Key Functions**:
- `generate()`: Convenience wrapper
- `get_generation()`: Convenience wrapper
- `list_generations()`: Convenience wrapper
- `download_model()`: Convenience wrapper

**Features**:
- Multipart form data for file uploads
- Automatic MIME type detection
- Bearer token authentication
- Configurable timeout (default 300s)
- HTTP error handling with detailed messages

**Environment Variables**:
- `PIXIBOX_API_ENDPOINT`: Base API URL
- `PIXIBOX_AUTH_TOKEN`: Authentication token
- `PIXIBOX_TIMEOUT`: Request timeout

### bridge.py — WebSocket Bridge

**Purpose**: Real-time generation status updates

**Key Classes**:
- `PixiboxBridge`: WebSocket client with methods:
  - `connect()`: Open WebSocket connection (spawns background thread)
  - `disconnect()`: Close connection
  - `on_generation_update()`: Register status callback
  - `on_error()`: Register error callback
  - `on_connected()`: Register connection callback
  - `wait()`: Block until generation completes
  - `is_connected()`: Check connection status

**Features**:
- Thread-safe callback dispatching
- Automatic reconnection with backoff
- Houdini-safe event queueing
- Optional debug logging

**Environment Variables**:
- `PIXIBOX_WEBSOCKET_ENDPOINT`: WebSocket URL
- `PIXIBOX_AUTH_TOKEN`: Authentication token
- `PIXIBOX_DEBUG`: Enable trace logging

**Threading Model**:
- Background thread runs `WebSocketApp.run_forever()`
- Callbacks dispatched via thread-safe queue
- Non-blocking `wait()` respects Houdini event loop

### lop_utils.py — Solaris/LOPs Integration

**Purpose**: USD stage manipulation and material conversion

**Key Functions**:
- `get_current_stage()`: Get active USD stage in Solaris
- `import_to_stage()`: Download and import model to USD prim
- `create_materialx_network()`: Create MaterialX shader network
- `optimize_mesh()`: Apply mesh decimation/cleanup

**Features**:
- Automatic GLB → USD import via LOPs nodes
- MaterialX material generation from textures
- PBR texture channel mapping
- Mesh optimization (placeholder for SOP integration)
- Thread-safe prim path handling

**Dependencies**:
- `pxr.Usd`: USD core
- `pxr.UsdGeom`: Geometry primitives
- `pxr.UsdShade`: Material networks
- `pxr.MaterialX`: Material exchange

**Error Handling**:
- Validates Solaris context (LOPs path check)
- Returns (node_path, metadata) tuples for error tracking
- Graceful fallback if MaterialX unavailable

### shelf_tools.py — User Interface

**Purpose**: Dialog boxes and shelf tool handlers

**Key Functions**:
- `generate_from_prompt()`: Text-to-3D dialog
- `generate_from_image()`: Image-to-3D with file picker
- `import_latest()`: Auto-import most recent generation
- `toggle_bridge()`: Connect/disconnect WebSocket bridge
- `open_settings()`: Configuration dialog

**Key Classes**:
- `PixiboxSettingsDialog`: Settings dialog with:
  - API endpoint configuration
  - Authentication token input
  - Default model selection
  - Material options (MaterialX, texture resolution)
  - Auto-import toggle

**Features**:
- Qt-based dialogs (Houdini native)
- Non-blocking modal dialogs
- Status label feedback during operations
- Form validation (prompt length, etc)
- Error message display

**Dialog Flows**:
1. User clicks shelf button
2. Dialog opens (blocks user input)
3. User configures options
4. OK/Cancel buttons apply or discard
5. Background task spawned (does not block)

### __init__.py — Public API

**Purpose**: Module exports and high-level API

**Exports**:
```python
# API functions
generate()
get_generation()
list_generations()
download_model()

# Classes
PixiboxClient
PixiboxBridge

# Solaris utilities
get_current_stage()
import_to_stage()
create_materialx_network()
```

**Usage Pattern**:
```python
from pixibox_houdini import generate, import_to_stage

gen_id = generate("text-to-3d", "A ceramic vase", "nvidia-edify")
import_to_stage(gen_id, "/World/Imports/Vase", apply_materialx=True)
```

## Houdini Integration Points

### Package Descriptor (pixibox.json)

```json
{
  "env": [{"PIXIBOX_HOUDINI": "$HOUDINI_PACKAGE_PATH/pixibox"}],
  "path": "$PIXIBOX_HOUDINI"
}
```

- Registers plugin with Houdini package system
- Sets `PIXIBOX_HOUDINI` environment variable
- Auto-loads shelf from `toolbar/` directory

### Startup Script (scripts/OnCreated.py)

Runs on Houdini launch:
1. Sets up `PIXIBOX_*` environment variables with defaults
2. Adds plugin `python/` to `sys.path`
3. Verifies dependencies (websocket-client, USD)
4. Registers shelf tools
5. Creates menu items (future)

### Shelf Definition (toolbar/pixibox.shelf)

XML-based shelf definition with tools:

```xml
<tool name="pixibox_prompt" label="Generate from Prompt">
  <script>
    from pixibox_houdini.shelf_tools import generate_from_prompt
    generate_from_prompt()
  </script>
</tool>
```

Each tool is a Python script that executes in Houdini's interpreter.

### HDAs (otls/pixibox_generate.hda)

Compiled in Houdini Desktop:
- Node type registered in plugin namespace
- Accessible via TAB menu → Pixibox section
- Parameters exposed via type definition
- Outputs geometry + metadata

## Type System

All Python modules use PEP 484 type hints for IDE autocomplete:

```python
def generate(
    mode: str,
    prompt: Optional[str] = None,
    image_path: Optional[str] = None,
    model: str = "nvidia-edify",
    **kwargs: Any,
) -> str:
    """Generate 3D model, return generation ID"""
```

**Typing Tools**:
- Type hints in function signatures
- Optional[] for nullable parameters
- Dict[str, Any] for flexible JSON data
- Return type annotations

## Authentication Flow

1. **Get Token**: User creates account at pixibox.ai, generates API token
2. **Set Token**: User sets `PIXIBOX_AUTH_TOKEN` environment variable or via Settings dialog
3. **Bearer Auth**: All requests include `Authorization: Bearer <token>` header
4. **Token Validation**: API validates token on each request
5. **Refresh**: Token expires after 90 days (user regenerates)

## Error Handling Strategy

### API Errors (api.py)
```python
try:
    urllib.request.urlopen(request, timeout=self.timeout)
except urllib.error.HTTPError as e:
    raise RuntimeError(f"API request failed: {e.code} {e.read()}")
```

### WebSocket Errors (bridge.py)
```python
def _on_ws_error(self, ws, error):
    self._dispatch_callback("error", f"WebSocket error: {error}")
    if self.auto_reconnect:
        time.sleep(5)
        self.connect()
```

### Import Errors (lop_utils.py)
```python
try:
    import_to_stage(...)
except Exception as e:
    return None, {"error": f"Import failed: {str(e)}"}
```

## Performance Considerations

### Multipart Upload Optimization
- Streams files without loading entire GLB into memory
- Automatic MIME type detection
- Boundary encoding done on-demand

### WebSocket Threading
- Background thread prevents UI blocking
- Event queue prevents race conditions
- `wait()` uses short sleep cycles (0.1s) to avoid busy-waiting

### USD Stage Operations
- Lazy evaluation where possible
- Batch prim creation in single calls
- Minimal traversal of stage hierarchy

## Security

### Authentication
- API tokens stored in environment (user responsibility)
- Bearer token authentication for all requests
- HTTPS/WSS for encrypted transport

### Input Validation
- File paths validated before upload
- Prim paths checked against USD schema
- User-provided prompts sent as-is (no injection risk)

### Sandboxing
- No file system access beyond specified paths
- No shell execution
- WebSocket limited to configured endpoint

## Future Extensions

### Potential Enhancements

1. **Batch Processing**: Queue multiple generations
2. **Model Library**: Local caching of frequently used models
3. **Advanced Materials**: Custom shader creation, layering
4. **Rigging Integration**: Auto-rig generated models
5. **Animation Export**: Frame sequences with materials
6. **Collaborative Tools**: Team asset library syncing
7. **Custom Nodes**: SOP/LOP nodes for generation pipeline

### Extension Points

- `PixiboxClient` can be subclassed for custom APIs
- `PixiboxBridge` callbacks can dispatch to custom handlers
- `lop_utils` functions can be wrapped with additional logic
- Shelf tools can be extended with additional dialogs

## Testing

### Unit Tests (planned)

```bash
pytest tests/
mypy python/  # Type checking
ruff check python/  # Linting
```

### Integration Tests (planned)

- Mock Houdini environment with dummy `hou` module
- Test API client against mock server
- Verify USD stage operations with pxr test stages

## Documentation

### User Documentation
- README.md: Installation, quick start, troubleshooting
- Inline docstrings: Each function has detailed help
- Shelf tool helpText: Context-sensitive help in Houdini

### Developer Documentation
- PLUGIN_ARCHITECTURE.md: This file
- Type hints: IDE autocomplete and mypy checking
- Code comments: Complex algorithms explained

## References

- [Houdini Python API](https://www.sidefx.com/docs/houdini/hom/)
- [Solaris/USD](https://www.sidefx.com/docs/houdini/solaris/)
- [MaterialX Specification](https://materialx.org/)
- [Pixibox API Documentation](https://docs.pixibox.ai/)
