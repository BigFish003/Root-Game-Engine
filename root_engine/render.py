"""Renderer facade and simple text/svg renderers."""

from __future__ import annotations

from .enums import Faction
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
        body_text = _multiline_svg_text(
            body_safe, x=10, y=50, line_height=16, font_size=12
        )

        side_panel = _vagabond_svg_panel(payload)
        if isinstance(payload, Observation):
            private = self._text.render_observer_private(payload)
            private_safe = _escape_svg_text(private)
            side_panel += (
                "<rect x='600' y='265' width='285' height='215' fill='#f5f5f5' stroke='#ccc'/>"
                "<text x='610' y='285' font-size='14'>Observer view</text>"
                + _multiline_svg_text(
                    private_safe, x=610, y=310, line_height=16, font_size=12
                )
            )

        return (
            "<svg xmlns='http://www.w3.org/2000/svg' width='900' height='500'>"
            "<text x='10' y='24' font-size='16'>Faction Status</text>"
            f"{body_text}"
            f"{side_panel}"
            "</svg>"
        )


def _escape_svg_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _multiline_svg_text(
    text: str, *, x: int, y: int, line_height: int, font_size: int
) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    tspans = [f"<tspan x='{x}' dy='0'>{lines[0]}</tspan>"]
    for line in lines[1:]:
        tspans.append(f"<tspan x='{x}' dy='{line_height}'>{line}</tspan>")
    return f"<text x='{x}' y='{y}' font-size='{font_size}'>{''.join(tspans)}</text>"


def _vagabond_svg_panel(payload: GameState | Observation) -> str:
    lines = _vagabond_lines(payload)
    if not lines:
        return ""
    text = _escape_svg_text("\n".join(lines))
    return (
        "<rect x='600' y='10' width='285' height='245' fill='#fff8e6' stroke='#d6b656'/>"
        "<text x='610' y='30' font-size='14'>Vagabond</text>"
        + _multiline_svg_text(text, x=610, y=55, line_height=15, font_size=11)
    )


def _vagabond_lines(payload: GameState | Observation) -> list[str]:
    if isinstance(payload, Observation):
        data = payload.factions[Faction.VAGABOND].public_data
        return [
            f"Location: {_format_vagabond_location(data.get('location'), data.get('forest_location'))}",
            f"Character: {data.get('character', 'unknown')}",
            f"Satchel: {_format_mapping(data.get('satchel', {}))}",
            f"Tracks: {_format_mapping(data.get('tracks', {}))}",
            f"Exhausted: {_format_mapping(data.get('exhausted_items', {}))}",
            f"Damaged: {_format_mapping(data.get('damaged_items', {}))}",
            f"Relations: {_format_mapping(data.get('relationships', {}))}",
            f"Crafted Cards: {_format_sequence(data.get('crafted_cards', []))}",
            f"Crafted Items: {_format_mapping(data.get('crafted_items', {}))}",
            f"Quests: {_format_sequence(data.get('quests_available', []))}",
            f"Ruins: {_format_ruin_items(data.get('ruin_items', {}))}",
        ]

    vagabond = payload.vagabond
    relationships = {
        faction.value: relation.value
        for faction, relation in vagabond.relationships.items()
    }
    return [
        f"Location: {_format_vagabond_location(vagabond.location, vagabond.forest_location)}",
        f"Character: {vagabond.character}",
        f"Satchel: {_format_mapping(_enum_mapping(vagabond.satchel))}",
        f"Tracks: {_format_mapping(_enum_mapping(vagabond.tracks))}",
        f"Exhausted: {_format_mapping(_enum_mapping(vagabond.exhausted_items))}",
        f"Damaged: {_format_mapping(_enum_mapping(vagabond.damaged_items))}",
        f"Relations: {_format_mapping(relationships)}",
        f"Crafted Cards: {_format_sequence(payload.crafted_cards.get(Faction.VAGABOND, []))}",
        f"Crafted Items: {_format_mapping(_enum_mapping(payload.crafted_items.get(Faction.VAGABOND, {})))}",
        f"Quests: {_format_sequence(vagabond.quests_available)}",
        f"Ruins: {_format_ruin_items({cid: [item.value for item in items] for cid, items in payload.board.ruin_items.items()})}",
    ]


def _format_vagabond_location(location: object, forest_location: object = None) -> str:
    if location in (None, ""):
        return "not in play"
    if location == 0:
        if forest_location in (None, ""):
            return "forest"
        return f"forest {forest_location}"
    return f"clearing {location}"


def _enum_mapping(mapping: dict) -> dict[str, object]:
    return {getattr(key, "value", str(key)): value for key, value in mapping.items()}


def _format_mapping(mapping: object) -> str:
    if not isinstance(mapping, dict) or not mapping:
        return "-"
    return ", ".join(f"{key}={value}" for key, value in sorted(mapping.items()))


def _format_sequence(values: object) -> str:
    if not values:
        return "-"
    return ", ".join(str(value) for value in values)


def _format_ruin_items(ruin_items: object) -> str:
    if not isinstance(ruin_items, dict) or not ruin_items:
        return "-"
    parts = []
    for clearing_id, items in sorted(
        ruin_items.items(), key=lambda entry: int(entry[0])
    ):
        item_text = "/".join(str(item) for item in items) if items else "empty"
        parts.append(f"c{clearing_id}:{item_text}")
    return ", ".join(parts)


def get_renderer(mode: str) -> TextRenderer | VisualRenderer:
    normalized = mode.strip().lower()
    if normalized == "visual":
        return VisualRenderer()
    return TextRenderer()
