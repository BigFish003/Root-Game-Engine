"""Renderer facade and simple text/svg renderers."""

from __future__ import annotations

from .models import GameState
from .observation import Observation
from .renderer import RootRenderer


class TextRenderer(RootRenderer):
    """Alias for the core plain-text renderer."""


class VisualRenderer:
    """Small SVG renderer suitable for tests and debugging."""

    def __init__(self) -> None:
        self._text = RootRenderer()

    def render(self, payload: GameState | Observation) -> str:
        body = self._text.render(payload)
        safe = (
            body.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return (
            "<svg xmlns='http://www.w3.org/2000/svg' width='900' height='500'>"
            "<text x='10' y='24' font-size='16'>Faction Status</text>"
            f"<text x='10' y='50' font-size='12'>{safe}</text>"
            "</svg>"
        )


def get_renderer(mode: str) -> TextRenderer | VisualRenderer:
    normalized = mode.strip().lower()
    if normalized == "visual":
        return VisualRenderer()
    return TextRenderer()
