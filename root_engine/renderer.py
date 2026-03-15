"""Backward-compatible renderer exports."""

from root_engine.render.text_renderer import TextRenderer
from root_engine.render.visual_renderer import VisualRenderer

# Preserve prior public API name.
RootRenderer = TextRenderer

__all__ = ["RootRenderer", "TextRenderer", "VisualRenderer"]
