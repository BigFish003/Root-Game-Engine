"""Crafting legal checks and helper utilities."""

from __future__ import annotations

from ..enums import BuildingType, CardTag, Faction, ItemType, Suit, TokenType
from ..models import Card, GameState


INITIAL_ITEM_SUPPLY: dict[ItemType, int] = {
    ItemType.BOOT: 2,
    ItemType.BAG: 2,
    ItemType.CROSSBOW: 1,
    ItemType.HAMMER: 1,
    ItemType.SWORD: 2,
    ItemType.TEAPOT: 2,
    ItemType.COIN: 2,
    ItemType.TORCH: 0,
}


def create_item_supply() -> dict[ItemType, int]:
    """Return the shared craftable item supply for setup."""

    return dict(INITIAL_ITEM_SUPPLY)


def legal_craft_cards(state: GameState, hand: list[int], faction: Faction) -> list[int]:
    """Return craftable cards from hand under faction crafting rules."""

    if faction == Faction.EYRIE:
        available = _eyrie_crafting_power(state)
        return _legal_from_power(state, hand, faction, available)
    if faction == Faction.ALLIANCE:
        available = _alliance_crafting_power(state)
        return _legal_from_power(state, hand, faction, available)
    if faction != Faction.MARQUISE:
        return [
            cid
            for cid in hand
            if cid in state.cards and can_craft_card_effect(state, faction, state.cards[cid])
        ]

    available = dict(state.marquise.crafting_power)
    return _legal_from_power(state, hand, faction, available)


def _legal_from_power(
    state: GameState,
    hand: list[int],
    faction: Faction,
    available: dict[Suit, int],
) -> list[int]:
    legal: list[int] = []
    for cid in hand:
        if cid not in state.cards:
            continue
        card = state.cards[cid]
        if not can_craft_card_effect(state, faction, card):
            continue
        if _can_pay(card.craft_cost, card.craft_cost_any, dict(available)):
            legal.append(cid)
    return legal


def can_craft_card_effect(state: GameState, faction: Faction, card: Card) -> bool:
    """Return whether a card's non-cost constraints allow crafting."""

    if not card.craftable:
        return False
    if (
        CardTag.PERSISTENT_EFFECT in card.tags
        and card.name in state.faction_state(faction).crafted_effects
    ):
        return False
    if card.item_reward is not None and state.item_supply.get(card.item_reward, 0) <= 0:
        return False
    return True


def record_crafted_card(state: GameState, faction: Faction, card_id: int) -> None:
    """Record that a faction crafted a card, including immediate cards."""

    crafted = state.crafted_cards.setdefault(faction, [])
    crafted.append(card_id)


def take_item_from_supply(state: GameState, item: ItemType) -> None:
    """Remove one item from the shared craftable item supply."""

    if state.item_supply.get(item, 0) <= 0:
        raise ValueError(f"No {item.value} items remain in the shared item supply")
    state.item_supply[item] -= 1


def add_crafted_item(state: GameState, faction: Faction, item: ItemType) -> None:
    crafted = state.crafted_items.setdefault(faction, {})
    crafted[item] = crafted.get(item, 0) + 1


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


def _eyrie_crafting_power(state: GameState) -> dict[Suit, int]:
    power = {Suit.FOX: 0, Suit.RABBIT: 0, Suit.MOUSE: 0}
    for cid, clearing in state.board.clearings.items():
        roost_count = sum(
            1 for building in state.board.buildings[cid][Faction.EYRIE] if building == BuildingType.ROOST
        )
        if roost_count > 0 and clearing.suit in power:
            power[clearing.suit] += roost_count
    return power


def _alliance_crafting_power(state: GameState) -> dict[Suit, int]:
    power = {Suit.FOX: 0, Suit.RABBIT: 0, Suit.MOUSE: 0}
    for cid, clearing in state.board.clearings.items():
        sympathy_count = sum(1 for token in state.board.tokens[cid][Faction.ALLIANCE] if token == TokenType.SYMPATHY)
        if sympathy_count > 0 and clearing.suit in power:
            power[clearing.suit] += sympathy_count
    return power


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
