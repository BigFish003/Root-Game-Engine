"""Renderer-only layout and styling constants for SVG visualizations."""

from __future__ import annotations

from root_engine.enums import Faction, Suit

BOARD_SIZE = (1280, 820)
BOARD_ORIGIN_X = 40
BOARD_ORIGIN_Y = 30
BOARD_PANEL_WIDTH = 830

CLEARING_COORDS: dict[int, tuple[int, int]] = {
    1: (120, 150),
    2: (280, 100),
    3: (450, 120),
    4: (170, 300),
    5: (340, 250),
    6: (520, 260),
    7: (690, 220),
    8: (260, 470),
    9: (430, 430),
    10: (610, 420),
    11: (760, 360),
    12: (700, 560),
}

FACTION_COLORS: dict[Faction, str] = {
    Faction.MARQUISE: "#d35400",
    Faction.EYRIE: "#2e86de",
    Faction.ALLIANCE: "#27ae60",
    Faction.VAGABOND: "#7f8c8d",
}

SUIT_COLORS: dict[Suit, str] = {
    Suit.FOX: "#fdebd0",
    Suit.RABBIT: "#fcf3cf",
    Suit.MOUSE: "#f5eef8",
    Suit.BIRD: "#ecf0f1",
}

BUILDING_ABBREVIATIONS = {
    "sawmill": "S",
    "workshop": "W",
    "recruiter": "R",
    "roost": "Roost",
    "base": "Base",
}

TOKEN_ABBREVIATIONS = {
    "wood": "Wood",
    "keep": "Keep",
    "sympathy": "Sym",
    "ruin": "Ruin",
    "vagabond": "Vag",
}
