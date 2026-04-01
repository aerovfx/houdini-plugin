"""
Pixibox Houdini Plugin — 3D AI Generation for Solaris/LOPs

This module provides a complete Python API for integrating Pixibox.ai
(3D AI tool comparison platform) with Houdini's Solaris (USD) environment.

Main functions:
    - generate(): Create 3D models from text or image prompts
    - import_to_stage(): Add generated models to USD stage with materials
    - get_generation(): Retrieve generation status and metadata
    - list_generations(): Browse past generations
    - download_model(): Fetch models in various formats

Classes:
    - PixiboxBridge: Real-time WebSocket sync with live progress updates
    - PixiboxClient: REST API client for Pixibox backend

Example:
    >>> from pixibox_houdini import generate, import_to_stage
    >>> gen_id = generate("text-to-3d", "A ceramic vase", "nvidia-edify")
    >>> import_to_stage(gen_id, "/World/Imports/Vase", apply_materialx=True)
"""

from .api import (
    PixiboxClient,
    generate,
    get_generation,
    list_generations,
    download_model,
)
from .bridge import PixiboxBridge
from .lop_utils import (
    get_current_stage,
    import_to_stage,
    create_materialx_network,
)

__version__ = "1.0.0"
__author__ = "Pixibox.ai"

__all__ = [
    "PixiboxClient",
    "PixiboxBridge",
    "generate",
    "get_generation",
    "list_generations",
    "download_model",
    "get_current_stage",
    "import_to_stage",
    "create_materialx_network",
]
