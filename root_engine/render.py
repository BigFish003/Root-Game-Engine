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
        body_safe = _escape_svg_text(body)
        body_text = _multiline_svg_text(body_safe, x=10, y=50, line_height=16, font_size=12)

        right_panel = ""
        if isinstance(payload, Observation):
            private = self._text.render_observer_private(payload)
            private_safe = _escape_svg_text(private)
            right_panel = (
                "<rect x='600' y='10' width='285' height='470' fill='#f5f5f5' stroke='#ccc'/>"
                "<text x='610' y='30' font-size='14'>Observer view</text>"
                + _multiline_svg_text(private_safe, x=610, y=55, line_height=16, font_size=12)
            )

        return (
            "<svg xmlns='http://www.w3.org/2000/svg' width='900' height='500'>"
            "<text x='10' y='24' font-size='16'>Faction Status</text>"
            f"{body_text}"
            f"{right_panel}"
            "</svg>"
        )


def _escape_svg_text(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _multiline_svg_text(text: str, *, x: int, y: int, line_height: int, font_size: int) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    tspans = [f"<tspan x='{x}' dy='0'>{lines[0]}</tspan>"]
    for line in lines[1:]:
        tspans.append(f"<tspan x='{x}' dy='{line_height}'>{line}</tspan>")
    return f"<text x='{x}' y='{y}' font-size='{font_size}'>{''.join(tspans)}</text>"


def get_renderer(mode: str) -> TextRenderer | VisualRenderer:
    normalized = mode.strip().lower()
    if normalized == "visual":
        return VisualRenderer()
    return TextRenderer()
