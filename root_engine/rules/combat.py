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
    attacker_hits, defender_hits = _battle_hits(attacker, defender)

    defender_losses = min(attacker_hits, state.board.warriors[clearing_id][defender])
    attacker_losses = min(defender_hits, state.board.warriors[clearing_id][attacker])

    if defender_losses > 0:
        state.board.warriors[clearing_id][defender] -= defender_losses
        state.scores[attacker] += defender_losses
    if attacker_losses > 0:
        state.board.warriors[clearing_id][attacker] -= attacker_losses
    _apply_field_hospitals(state, clearing_id, defender, defender_losses)
    _apply_field_hospitals(state, clearing_id, attacker, attacker_losses)


def _battle_hits(attacker: Faction, defender: Faction) -> tuple[int, int]:
    """Return attacker and defender hit counts for simplified battle."""

    attacker_roll = 1
    defender_roll = 1
    if defender == Faction.ALLIANCE:
        return max(attacker_roll, defender_roll), min(attacker_roll, defender_roll)
    return attacker_roll, defender_roll


def _apply_field_hospitals(
    state: GameState,
    clearing_id: int,
    faction_with_losses: Faction,
    losses: int,
) -> None:
    if faction_with_losses != Faction.MARQUISE or losses <= 0:
        return
    keep = state.marquise.keep_clearing
    if keep is None:
        return
    clearing_suit = state.board.clearings[clearing_id].suit
    matching = [card_id for card_id in state.marquise.hand if state.cards[card_id].suit == clearing_suit]
    if not matching:
        return
    state.marquise.hand.remove(matching[0])
    state.discard_pile.append(matching[0])
    state.board.warriors[keep][Faction.MARQUISE] += losses
