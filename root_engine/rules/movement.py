"""Shared movement rule checks."""

from __future__ import annotations

from ..enums import Faction
from ..models import GameState


def legal_move_sources(state: GameState, faction: Faction) -> list[int]:
    """Return clearings containing at least one warrior for the faction."""

    return [
        cid
        for cid, by_faction in state.board.warriors.items()
        if by_faction.get(faction, 0) > 0
    ]


def legal_move_destinations(state: GameState, source: int) -> list[int]:
    """Return all adjacent clearings from source (rule simplification)."""

    return list(state.board.clearings[source].adjacent_clearings)
