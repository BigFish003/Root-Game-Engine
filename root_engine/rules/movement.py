"""Shared movement rule checks."""

from __future__ import annotations

from ..enums import Faction
from ..models import GameState
from .rulership import rules_clearing


def legal_move_sources(state: GameState, faction: Faction) -> list[int]:
    """Return clearings containing at least one warrior and a legal destination."""

    return [
        cid
        for cid, by_faction in state.board.warriors.items()
        if by_faction.get(faction, 0) > 0
        and legal_move_destinations(state, faction, cid)
    ]


def legal_move_destinations(state: GameState, faction: Faction, source: int) -> list[int]:
    """Return adjacent clearings where move rule is satisfied (rule source, destination, or both)."""

    rules_origin = rules_clearing(state, source, faction)
    return [
        destination
        for destination in state.board.clearings[source].adjacent_clearings
        if rules_origin or rules_clearing(state, destination, faction)
    ]
