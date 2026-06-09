"""Base map definition for Root using a graph representation."""

from __future__ import annotations

from .enums import Suit
from .models import Clearing, Forest


# Simplified base map metadata with the standard 12 clearings.
BASE_CLEARINGS: dict[int, tuple[Suit, int, list[int]]] = {
    1: (Suit.FOX, 1, [2, 4, 5]),
    2: (Suit.RABBIT, 2, [1, 3]),
    3: (Suit.MOUSE, 2, [2, 5,8]),
    4: (Suit.MOUSE, 2, [1, 6, 9]),
    5: (Suit.RABBIT, 1, [1, 3, 6]),
    6: (Suit.FOX, 1, [4, 5, 7,9,11]),
    7: (Suit.MOUSE, 2, [6,8,12]),
    8: (Suit.FOX, 1, [3,7,12]),
    9: (Suit.RABBIT, 1, [4,6,10]),
    10: (Suit.FOX, 2, [9,11]),
    11: (Suit.MOUSE, 2, [6,10,12]),
    12: (Suit.RABBIT, 1, [7,8,11]),
}

RUIN_CLEARINGS = {3, 6, 9, 12}

# Forest regions are the faces of this simplified map graph. They are used by
# the Vagabond, whose pawn can be in a clearing or a forest.
BASE_FORESTS: dict[int, list[int]] = {
    1: [1, 2, 3, 5],
    2: [1, 2, 3, 4, 8, 9, 10, 11, 12],
    3: [1, 4, 5, 6],
    4: [3, 5, 6, 7, 8],
    5: [4, 6, 9],
    6: [6, 7, 11, 12],
    7: [6, 9, 10, 11],
    8: [7, 8, 12],
}

BASE_FOREST_ADJACENCIES: dict[int, list[int]] = {
    1: [2, 3, 4],
    2: [1, 3, 4, 5, 6, 7, 8],
    3: [1, 2, 4, 5],
    4: [1, 2, 3, 6, 8],
    5: [2, 3, 7],
    6: [2, 4, 7, 8],
    7: [2, 5, 6],
    8: [2, 4, 6],
}


def create_base_map() -> dict[int, Clearing]:
    """Create clearing definitions for the standard base map."""

    clearings: dict[int, Clearing] = {}
    for clearing_id, (suit, slots, adjacent) in BASE_CLEARINGS.items():
        clearings[clearing_id] = Clearing(
            clearing_id=clearing_id,
            suit=suit,
            building_slots=slots,
            adjacent_clearings=list(adjacent),
            adjacent_forests=[
                forest_id
                for forest_id, forest_clearings in BASE_FORESTS.items()
                if clearing_id in forest_clearings
            ],
            has_ruin=clearing_id in RUIN_CLEARINGS,
        )
    return clearings


def create_base_forests() -> dict[int, Forest]:
    """Create forest definitions for the simplified base map."""

    return {
        forest_id: Forest(
            forest_id=forest_id,
            adjacent_clearings=list(adjacent_clearings),
            adjacent_forests=list(BASE_FOREST_ADJACENCIES[forest_id]),
        )
        for forest_id, adjacent_clearings in BASE_FORESTS.items()
    }
