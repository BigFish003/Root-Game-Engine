"""Crafting placeholders and basic legal checks."""

from __future__ import annotations

from ..models import GameState


def legal_craft_cards(state: GameState, hand: list[int]) -> list[int]:
    """Currently allow crafting any non-dominance card in hand."""

    return [cid for cid in hand if state.cards[cid].name != "Dominance"]
