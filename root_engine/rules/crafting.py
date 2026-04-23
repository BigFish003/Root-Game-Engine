"""Crafting legal checks and helper utilities."""

from __future__ import annotations

from ..enums import BuildingType, Faction, Suit
from ..models import GameState


def legal_craft_cards(state: GameState, hand: list[int], faction: Faction) -> list[int]:
    """Return craftable cards from hand under faction crafting rules."""

    if faction != Faction.MARQUISE:
        return [cid for cid in hand if state.cards[cid].craftable]

    available = dict(state.marquise.crafting_power)
    legal: list[int] = []
    for cid in hand:
        card = state.cards[cid]
        if not card.craftable:
            continue
        if _can_pay(card.craft_cost, card.craft_cost_any, available):
            legal.append(cid)
    return legal


def initialize_marquise_crafting_power(state: GameState) -> None:
    """Reset Marquise available craft slots from current workshops."""

    power = {Suit.FOX: 0, Suit.RABBIT: 0, Suit.MOUSE: 0}
    for cid, clearing in state.board.clearings.items():
        workshops = sum(
            1
            for building in state.board.buildings[cid][Faction.MARQUISE]
            if building == BuildingType.WORKSHOP
        )
        if workshops > 0:
            power[clearing.suit] += workshops
    state.marquise.crafting_power = power


def spend_marquise_crafting_power(state: GameState, card_id: int) -> None:
    """Spend Marquise crafting slots for the selected card."""

    card = state.cards[card_id]
    remaining = dict(state.marquise.crafting_power)
    _pay_cost(card.craft_cost, card.craft_cost_any, remaining)
    state.marquise.crafting_power = remaining


def _can_pay(cost: dict[Suit, int], any_cost: int, available: dict[Suit, int]) -> bool:
    try:
        _pay_cost(cost, any_cost, dict(available))
    except ValueError:
        return False
    return True


def _pay_cost(cost: dict[Suit, int], any_cost: int, available: dict[Suit, int]) -> None:
    for suit, amount in cost.items():
        if available.get(suit, 0) < amount:
            raise ValueError("Missing suited crafting power")
        available[suit] -= amount
    for _ in range(any_cost):
        suit = max((Suit.FOX, Suit.RABBIT, Suit.MOUSE), key=lambda s: available[s])
        if available[suit] <= 0:
            raise ValueError("Missing wildcard crafting power")
        available[suit] -= 1
