"""Card pool for the simplified base-game engine."""

from __future__ import annotations

from .enums import CardTag, Suit
from .models import Card


BASE_DECK_SPECS: list[dict] = [
    # Bird suit (13)
    {"name": "Armorers", "suit": Suit.BIRD, "tags": (CardTag.PERSISTENT_EFFECT,), "count": 2, "cost": {Suit.FOX: 1}},
    {"name": "Sappers", "suit": Suit.BIRD, "tags": (CardTag.PERSISTENT_EFFECT,), "count": 2, "cost": {Suit.MOUSE: 1}},
    {"name": "Brutal Tactics", "suit": Suit.BIRD, "tags": (CardTag.PERSISTENT_EFFECT,), "count": 2, "cost": {Suit.FOX: 2}},
    {"name": "Royal Claim", "suit": Suit.BIRD, "tags": (CardTag.PERSISTENT_EFFECT,), "count": 1, "cost_any": 4},
    {"name": "Birdy Bindle", "suit": Suit.BIRD, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.MOUSE: 1}, "vp": 1},
    {"name": "Woodland Runners", "suit": Suit.BIRD, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.RABBIT: 1}, "vp": 1},
    {"name": "Arms Trader", "suit": Suit.BIRD, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.FOX: 2}, "vp": 2},
    {"name": "Crossbow", "suit": Suit.BIRD, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.FOX: 1}, "vp": 1},
    {"name": "Ambush!", "suit": Suit.BIRD, "tags": (CardTag.AMBUSH,), "count": 1, "craftable": False},
    {"name": "Dominance", "suit": Suit.BIRD, "tags": (CardTag.DOMINANCE,), "count": 1, "craftable": False},
    # Rabbit suit (13)
    {"name": "Better Burrow Bank", "suit": Suit.RABBIT, "tags": (CardTag.PERSISTENT_EFFECT,), "count": 2, "cost": {Suit.RABBIT: 2}},
    {"name": "Cobbler", "suit": Suit.RABBIT, "tags": (CardTag.PERSISTENT_EFFECT,), "count": 2, "cost": {Suit.RABBIT: 2}},
    {"name": "Command Warren", "suit": Suit.RABBIT, "tags": (CardTag.PERSISTENT_EFFECT,), "count": 2, "cost": {Suit.RABBIT: 2}},
    {"name": "Bake Sale", "suit": Suit.RABBIT, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.RABBIT: 2}, "vp": 3},
    {"name": "Smuggler's Trail", "suit": Suit.RABBIT, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.MOUSE: 1}, "vp": 1},
    {"name": "Root Tea", "suit": Suit.RABBIT, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.MOUSE: 1}, "vp": 2},
    {"name": "A Visit to Friends", "suit": Suit.RABBIT, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.RABBIT: 1}, "vp": 1},
    {"name": "Favor of the Rabbits", "suit": Suit.RABBIT, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.RABBIT: 3}},
    {"name": "Ambush!", "suit": Suit.RABBIT, "tags": (CardTag.AMBUSH,), "count": 1, "craftable": False},
    {"name": "Dominance", "suit": Suit.RABBIT, "tags": (CardTag.DOMINANCE,), "count": 1, "craftable": False},
    # Mouse suit (13)
    {"name": "Codebreakers", "suit": Suit.MOUSE, "tags": (CardTag.PERSISTENT_EFFECT,), "count": 2, "cost": {Suit.MOUSE: 1}},
    {"name": "Scouting Party", "suit": Suit.MOUSE, "tags": (CardTag.PERSISTENT_EFFECT,), "count": 2, "cost": {Suit.MOUSE: 2}},
    {"name": "Crossbow", "suit": Suit.MOUSE, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.FOX: 1}, "vp": 1},
    {"name": "Sword", "suit": Suit.MOUSE, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.FOX: 2}, "vp": 2},
    {"name": "Travel Gear", "suit": Suit.MOUSE, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.RABBIT: 1}, "vp": 1},
    {"name": "Investments", "suit": Suit.MOUSE, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.RABBIT: 2}, "vp": 3},
    {"name": "Favor of the Mice", "suit": Suit.MOUSE, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.MOUSE: 3}},
    {"name": "Root Tea", "suit": Suit.MOUSE, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.MOUSE: 1}, "vp": 2},
    {"name": "Mouse-in-a-Sack", "suit": Suit.MOUSE, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.MOUSE: 1}, "vp": 1},
    {"name": "Ambush!", "suit": Suit.MOUSE, "tags": (CardTag.AMBUSH,), "count": 1, "craftable": False},
    {"name": "Dominance", "suit": Suit.MOUSE, "tags": (CardTag.DOMINANCE,), "count": 1, "craftable": False},
    # Fox suit (14)
    {"name": "Stand and Deliver!", "suit": Suit.FOX, "tags": (CardTag.PERSISTENT_EFFECT,), "count": 2, "cost": {Suit.MOUSE: 3}},
    {"name": "Tax Collector", "suit": Suit.FOX, "tags": (CardTag.PERSISTENT_EFFECT,), "count": 3, "cost": {Suit.RABBIT: 1, Suit.FOX: 1, Suit.MOUSE: 1}},
    {"name": "Root Tea", "suit": Suit.FOX, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.MOUSE: 1}, "vp": 2},
    {"name": "Protection Racket", "suit": Suit.FOX, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.RABBIT: 2}, "vp": 3},
    {"name": "Travel Gear", "suit": Suit.FOX, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.RABBIT: 1}, "vp": 1},
    {"name": "Gently Used Knapsack", "suit": Suit.FOX, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.MOUSE: 1}, "vp": 1},
    {"name": "Favor of the Foxes", "suit": Suit.FOX, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.FOX: 3}},
    {"name": "Foxfolk Steel", "suit": Suit.FOX, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.FOX: 2}, "vp": 2},
    {"name": "Anvil", "suit": Suit.FOX, "tags": (CardTag.ITEM,), "count": 1, "cost": {Suit.FOX: 1}, "vp": 2},
    {"name": "Ambush!", "suit": Suit.FOX, "tags": (CardTag.AMBUSH,), "count": 1, "craftable": False},
    {"name": "Dominance", "suit": Suit.FOX, "tags": (CardTag.DOMINANCE,), "count": 1, "craftable": False},
]


def create_base_deck() -> list[Card]:
    """Generate the base deck card list."""

    cards: list[Card] = []
    card_id = 1
    for spec in BASE_DECK_SPECS:
        for _ in range(spec["count"]):
            cards.append(
                Card(
                    card_id=card_id,
                    name=spec["name"],
                    suit=spec["suit"],
                    tags=spec.get("tags", ()),
                    craft_cost=dict(spec.get("cost", {})),
                    craft_cost_any=spec.get("cost_any", 0),
                    craftable=spec.get("craftable", True),
                    vp_on_craft=spec.get("vp", 0),
                )
            )
            card_id += 1
    return cards
