"""Shared battle helpers for simplified combat resolution."""

from __future__ import annotations

from ..enums import Faction, TokenType
from ..models import GameState
from . import alliance


def legal_battle_clearings(state: GameState, attacker: Faction) -> list[int]:
    """Clearings where attacker and at least one enemy coexist."""

    result: list[int] = []
    for cid, warriors in state.board.warriors.items():
        if warriors[attacker] <= 0:
            continue
        enemies = [
            f
            for f in Faction
            if f != attacker
            and (
                warriors[f] > 0
                or bool(state.board.buildings[cid][f])
                or bool(state.board.tokens[cid][f])
            )
        ]
        if enemies:
            result.append(cid)
    return result


def legal_battle_targets(state: GameState, attacker: Faction, clearing_id: int) -> list[Faction]:
    """Enemy factions with pieces present in the selected clearing."""

    warriors = state.board.warriors[clearing_id]
    return [
        f
        for f in Faction
        if f != attacker
        and (
            warriors[f] > 0
            or bool(state.board.buildings[clearing_id][f])
            or bool(state.board.tokens[clearing_id][f])
        )
    ]


def resolve_basic_battle(
    state: GameState,
    attacker: Faction,
    defender: Faction,
    clearing_id: int,
    attacker_extra_hits: int = 0,
    despot_bonus: bool = False,
) -> None:
    """Simplified deterministic battle: each side loses one warrior if available."""
    attacker_hits, defender_hits = _battle_hits(state, attacker, defender, clearing_id)

    defender_losses = min(attacker_hits, state.board.warriors[clearing_id][defender])
    attacker_losses = min(defender_hits, state.board.warriors[clearing_id][attacker])
    remaining_attacker_hits = attacker_hits - defender_losses

    if defender_losses > 0:
        state.board.warriors[clearing_id][defender] -= defender_losses
    if remaining_attacker_hits > 0:
        removed = _remove_defender_cardboard(state, attacker, defender, clearing_id, remaining_attacker_hits)
        if removed:
            state.scores[attacker] += removed
    if attacker_losses > 0:
        state.board.warriors[clearing_id][attacker] -= attacker_losses
    _apply_field_hospitals(state, clearing_id, defender, defender_losses)
    _apply_field_hospitals(state, clearing_id, attacker, attacker_losses)


def _battle_hits(state: GameState, attacker: Faction, defender: Faction, clearing_id: int) -> tuple[int, int]:
    """Return attacker and defender hit counts for simplified battle."""

    attacker_roll = 1
    defender_roll = 1
    if state.board.warriors[clearing_id][defender] <= 0:
        attacker_roll += 1  # Defenseless.
        defender_roll = 0
    return attacker_roll, defender_roll


def _remove_defender_cardboard(
    state: GameState,
    attacker: Faction,
    defender: Faction,
    clearing_id: int,
    hits: int,
) -> int:
    removed = 0
    tokens = state.board.tokens[clearing_id][defender]
    sympathy_removed = 0
    while hits > 0 and tokens:
        token = tokens.pop()
        removed += 1
        hits -= 1
        if token == TokenType.SYMPATHY:
            sympathy_removed += 1
    buildings = state.board.buildings[clearing_id][defender]
    while hits > 0 and buildings:
        buildings.pop()
        removed += 1
        hits -= 1
    if sympathy_removed:
        alliance.sync_sympathy_supply(state)
    for _ in range(sympathy_removed):
        alliance.trigger_outrage(state, attacker, clearing_id, require_sympathy_present=False)
    return removed


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
