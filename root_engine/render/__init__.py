"""Renderer entry points kept separate from engine internals."""

from root_engine.render.text_renderer import TextRenderer
from root_engine.render.visual_renderer import VisualRenderer


def get_renderer(mode: str) -> TextRenderer | VisualRenderer:
    if mode == "text":
        return TextRenderer()
    if mode == "visual":
        return VisualRenderer()
    raise ValueError(f"Unknown renderer mode: {mode}")


__all__ = ["TextRenderer", "VisualRenderer", "get_renderer"]
