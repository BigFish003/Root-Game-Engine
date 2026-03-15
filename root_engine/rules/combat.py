"""Shared battle helpers for simplified combat resolution."""

from __future__ import annotations

from ..enums import Faction
from ..models import GameState


def legal_battle_clearings(state: GameState, attacker: Faction) -> list[int]:
    """Clearings where attacker and at least one enemy coexist."""

    result: list[int] = []
    for cid, warriors in state.board.warriors.items():
        if warriors[attacker] <= 0:
            continue
        enemies = [f for f in Faction if f != attacker and warriors[f] > 0]
        if enemies:
            result.append(cid)
    return result


def legal_battle_targets(state: GameState, attacker: Faction, clearing_id: int) -> list[Faction]:
    """Enemy factions with pieces present in the selected clearing."""

    warriors = state.board.warriors[clearing_id]
    return [f for f in Faction if f != attacker and warriors[f] > 0]


def resolve_basic_battle(state: GameState, attacker: Faction, defender: Faction, clearing_id: int) -> None:
    """Simplified deterministic battle: each side loses one warrior if available."""

    if state.board.warriors[clearing_id][defender] > 0:
        state.board.warriors[clearing_id][defender] -= 1
        state.scores[attacker] += 1
    if state.board.warriors[clearing_id][attacker] > 0:
        state.board.warriors[clearing_id][attacker] -= 1
