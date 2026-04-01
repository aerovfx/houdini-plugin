# Contributing to Pixibox Houdini Plugin

Thank you for your interest in contributing to the Pixibox Houdini plugin! This document provides guidelines for development, testing, and submission.

## Development Setup

### Prerequisites

- Houdini 19.5+ (installed and licensed)
- Python 3.9+
- Git
- `pip` for Python package management

### Clone & Install

```bash
# Clone the plugin repository
git clone https://github.com/pixibox-ai/houdini-plugin ~/houdini19.5/packages/pixibox

# Set up development environment
cd ~/houdini19.5/packages/pixibox

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
```

### requirements-dev.txt

```
websocket-client>=11.0
pytest>=7.0
mypy>=1.0
ruff>=0.1.0
black>=23.0
```

## Code Style

### Type Hints

All Python code must include type hints:

```python
from typing import Optional, Dict, Any

def generate(
    mode: str,
    prompt: Optional[str] = None,
    image_path: Optional[str] = None,
) -> str:
    """Generate 3D model."""
    pass
```

Run `mypy` to check:
```bash
mypy python/pixibox_houdini
```

### Code Formatting

Use `black` for consistent formatting:

```bash
black python/pixibox_houdini
```

Use `ruff` for linting:

```bash
ruff check python/pixibox_houdini
```

### Docstrings

Follow Google-style docstrings:

```python
def import_to_stage(
    generation_id: str,
    prim_path: str = "/World/Imports/Model",
) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Import generated model to USD stage.

    Downloads the GLB model and imports it to the specified prim path
    in the current USD stage, optionally applying MaterialX materials.

    Args:
        generation_id: Pixibox generation ID
        prim_path: Target prim path (e.g. "/World/Imports/Vase")

    Returns:
        Tuple of (import_node_path, metadata_dict) or (None, error_dict)

    Raises:
        RuntimeError: If import fails

    Example:
        >>> node_path, meta = import_to_stage("gen-123", "/World/Imports/Vase")
        >>> if node_path:
        ...     print(f"Imported to {node_path}")
    """
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=python/pixibox_houdini tests/
```

### Writing Tests

Create test files in `tests/` directory matching module names:

```python
# tests/test_api.py
import pytest
from pixibox_houdini.api import PixiboxClient

class TestPixiboxClient:
    def test_health_check_success(self):
        client = PixiboxClient(endpoint="https://api.mock", token="test-token")
        # Mock the HTTP request
        # assert client.health_check() == True

    def test_generate_invalid_mode(self):
        client = PixiboxClient(token="test-token")
        with pytest.raises(ValueError):
            client.generate(mode="invalid")
```

### Mock Houdini Environment

For testing outside Houdini, create mock modules:

```python
# tests/conftest.py
import sys
from unittest.mock import MagicMock

# Mock hou module
sys.modules['hou'] = MagicMock()
sys.modules['pxr'] = MagicMock()

# Now you can import pixibox_houdini without Houdini
from pixibox_houdini import PixiboxClient
```

## Committing Changes

### Commit Message Format

Follow conventional commits:

```
feat: Add real-time progress monitoring

- Add PixiboxBridge WebSocket integration
- Implement on_generation_update callback
- Add wait() for blocking operations

Closes #42
```

### Branching Strategy

- Create feature branches from `main`
- Use descriptive names: `feature/mesh-optimization`, `fix/api-timeout`, etc
- Prefix commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes with type hints and docstrings
4. **Test** your code: `pytest tests/`
5. **Lint** your code: `ruff check python/` and `black python/`
6. **Type-check**: `mypy python/pixibox_houdini`
7. **Commit** with descriptive messages
8. **Push** to your fork
9. **Create** a Pull Request with:
   - Clear title and description
   - Reference any related issues
   - List testing steps
   - Include before/after screenshots if UI changes

## Reporting Issues

### Bug Report Template

```
## Description
Brief description of the bug

## Steps to Reproduce
1. Open Houdini
2. Go to Solaris tab
3. Click "Generate from Prompt"
4. ...

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- Houdini: 19.5.x
- Plugin Version: 1.0.0
- OS: Linux/Mac/Windows
- Python: 3.9.x

## Error Message
[Paste full error/traceback]
```

### Feature Request Template

```
## Description
Clear description of the feature

## Use Case
Why this feature is needed

## Proposed Solution
How you would implement it

## Alternatives
Other approaches considered
```

## Documentation

### Updating Docstrings

When modifying functions, update docstrings:

```python
def download_model(
    generation_id: str,
    format: str = "glb",
    output_path: Optional[str] = None,
) -> str:
    """Download generated 3D model.

    Args:
        generation_id: Generation ID to download
        format: Output format (glb, gltf, obj)
        output_path: Where to save. Defaults to temp dir.

    Returns:
        Local file path to downloaded model

    Raises:
        RuntimeError: If generation not completed

    Example:
        >>> path = download_model("gen-123", "glb")
    """
```

### Updating README.md

- Keep user-facing documentation current
- Add examples for new features
- Document breaking changes in CHANGELOG section

### Updating PLUGIN_ARCHITECTURE.md

- Document internal changes
- Update module diagrams if structure changes
- Add notes about new extension points

## Performance Guidelines

### API Calls

- Use pagination for listing operations
- Set reasonable timeouts (300s default)
- Cache responses when appropriate
- Implement rate limiting awareness

### Threading

- All callbacks must be thread-safe
- Use locks for shared state
- Avoid blocking operations in callbacks
- Use queues for cross-thread communication

### Memory

- Stream large files rather than buffering
- Clean up temporary files
- Lazy-load USD stages when possible
- Profile with `memory_profiler` for large assets

## Security Guidelines

### Authentication

- Never hardcode tokens
- Store tokens in environment variables only
- Support token rotation
- Validate token expiration

### Input Validation

- Validate file paths are within allowed directories
- Check file sizes before uploading
- Validate prim paths against USD schema
- Escape user prompts (no injection risk with current API)

### Sensitive Data

- Never log API tokens
- Don't store credentials in files
- Use HTTPS/WSS for all communication
- Handle errors without exposing internal details

## Release Process

### Version Numbers

Follow semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking API changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Checklist

- [ ] Update `__version__` in `__init__.py`
- [ ] Update CHANGELOG.md with release notes
- [ ] Run all tests and linting
- [ ] Create git tag: `git tag v1.0.1`
- [ ] Push tag: `git push origin v1.0.1`
- [ ] Create GitHub release with notes
- [ ] Update documentation site

## Getting Help

- **Issues**: Check existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Discord**: Join our community on Discord
- **Email**: support@pixibox.ai for security issues

## Code Review Guidelines

When reviewing code:

1. **Type Safety**: Verify all functions have type hints
2. **Documentation**: Check docstrings are complete
3. **Testing**: Ensure test coverage for new code
4. **Performance**: Look for optimization opportunities
5. **Security**: Check for authentication/validation issues
6. **Style**: Verify consistent formatting
7. **Compatibility**: Ensure works with Houdini 19.5+

## Resources

- [Houdini Python API](https://www.sidefx.com/docs/houdini/hom/)
- [Solaris/USD Documentation](https://www.sidefx.com/docs/houdini/solaris/)
- [PEP 484 Type Hints](https://www.python.org/dev/peps/pep-0484/)
- [Google Style Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [Conventional Commits](https://www.conventionalcommits.org/)

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

Thank you for helping make Pixibox Houdini better!
