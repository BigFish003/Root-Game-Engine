"""Base map definition for Root using a graph representation."""

from __future__ import annotations

from .enums import Suit
from .models import Clearing


# Simplified base map metadata with the standard 12 clearings.
BASE_CLEARINGS: dict[int, tuple[Suit, int, list[int]]] = {
    1: (Suit.FOX, 1, [2, 4, 5]),
    2: (Suit.RABBIT, 2, [1, 3, 6]),
    3: (Suit.MOUSE, 1, [2, 7]),
    4: (Suit.MOUSE, 2, [1, 5, 8]),
    5: (Suit.RABBIT, 2, [1, 4, 6, 9]),
    6: (Suit.FOX, 1, [2, 5, 7, 10]),
    7: (Suit.RABBIT, 2, [3, 6, 11]),
    8: (Suit.FOX, 2, [4, 9, 12]),
    9: (Suit.MOUSE, 1, [5, 8, 10]),
    10: (Suit.RABBIT, 2, [6, 9, 11]),
    11: (Suit.FOX, 1, [7, 10, 12]),
    12: (Suit.MOUSE, 2, [8, 11]),
}

RUIN_CLEARINGS = {3, 6, 9, 12}


def create_base_map() -> dict[int, Clearing]:
    """Create clearing definitions for the standard base map."""

    clearings: dict[int, Clearing] = {}
    for clearing_id, (suit, slots, adjacent) in BASE_CLEARINGS.items():
        clearings[clearing_id] = Clearing(
            clearing_id=clearing_id,
            suit=suit,
            building_slots=slots,
            adjacent_clearings=list(adjacent),
            has_ruin=clearing_id in RUIN_CLEARINGS,
        )
    return clearings
