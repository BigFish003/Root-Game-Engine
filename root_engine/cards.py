"""Card pool for the simplified base-game engine."""

from __future__ import annotations

from .enums import CardTag, Suit
from .models import Card


BASE_DECK_SPECS: list[tuple[str, Suit, tuple[CardTag, ...], int]] = [
    ("Ambush", Suit.FOX, (CardTag.AMBUSH,), 2),
    ("Ambush", Suit.RABBIT, (CardTag.AMBUSH,), 2),
    ("Ambush", Suit.MOUSE, (CardTag.AMBUSH,), 2),
    ("Travel Gear", Suit.BIRD, (CardTag.ITEM,), 3),
    ("Root Tea", Suit.BIRD, (CardTag.ITEM,), 2),
    ("Scouting Party", Suit.RABBIT, (CardTag.PERSISTENT_EFFECT,), 2),
    ("Command Warren", Suit.FOX, (CardTag.PERSISTENT_EFFECT,), 2),
    ("Tax Collector", Suit.MOUSE, (CardTag.PERSISTENT_EFFECT,), 2),
    ("Dominance", Suit.BIRD, (CardTag.DOMINANCE,), 4),
]


def create_base_deck() -> list[Card]:
    """Generate the base deck card list."""

    cards: list[Card] = []
    card_id = 1
    for name, suit, tags, count in BASE_DECK_SPECS:
        for _ in range(count):
            cards.append(Card(card_id=card_id, name=name, suit=suit, tags=tags))
            card_id += 1
    return cards
