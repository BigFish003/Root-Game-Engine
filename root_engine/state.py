"""Game state creation and cloning helpers."""

from __future__ import annotations

import copy
import random
from typing import Optional

from .cards import create_base_deck
from .enums import BuildingType, Faction, TokenType
from .map_data import create_base_map
from .models import (
    AllianceState,
    BoardState,
    DecisionContext,
    EyrieState,
    GameState,
    MarquiseState,
    TurnState,
    VagabondState,
)


def create_initial_state(seed: Optional[int] = None) -> GameState:
    """Create and setup a new game state."""

    rng = random.Random(seed)
    clearings = create_base_map()
    board = BoardState(
        clearings=clearings,
        warriors={cid: {f: 0 for f in Faction} for cid in clearings},
        buildings={cid: {f: [] for f in Faction} for cid in clearings},
        tokens={cid: {f: [] for f in Faction} for cid in clearings},
    )

    cards = create_base_deck()
    card_lookup = {c.card_id: c for c in cards}
    draw_pile = [c.card_id for c in cards]
    rng.shuffle(draw_pile)

    state = GameState(
        seed=seed,
        board=board,
        cards=card_lookup,
        draw_pile=draw_pile,
        discard_pile=[],
        scores={f: 0 for f in Faction},
        dominance_holder=None,
        marquise=MarquiseState(),
        eyrie=EyrieState(),
        alliance=AllianceState(),
        vagabond=VagabondState(),
        turn=TurnState(),
        decision_context=DecisionContext(),
    )
    _setup_starting_positions(state)
    _deal_opening_hands(state)
    return state


def clone_state(state: GameState) -> GameState:
    """Deep-copy state for search/testing."""

    return copy.deepcopy(state)


def _setup_starting_positions(state: GameState) -> None:
    # Marquise opening: keep + one sawmill/workshop/recruiter + warriors concentrated.
    keep = 1
    state.marquise.keep_clearing = keep
    state.board.tokens[keep][Faction.MARQUISE].append(TokenType.KEEP)
    state.board.buildings[keep][Faction.MARQUISE].append(BuildingType.SAWMILL)
    state.board.buildings[2][Faction.MARQUISE].append(BuildingType.WORKSHOP)
    state.board.buildings[4][Faction.MARQUISE].append(BuildingType.RECRUITER)
    state.marquise.buildings_in_supply[BuildingType.SAWMILL] -= 1
    state.marquise.buildings_in_supply[BuildingType.WORKSHOP] -= 1
    state.marquise.buildings_in_supply[BuildingType.RECRUITER] -= 1
    for cid in [1, 2,3, 4, 5, 6,7, 8,9, 10, 11]:
        state.board.warriors[cid][Faction.MARQUISE] = 1
        state.marquise.warriors_in_supply -= 1

    # Eyrie opening
    state.board.buildings[12][Faction.EYRIE].append(BuildingType.ROOST)
    state.eyrie.roosts_in_supply -= 1
    state.board.warriors[12][Faction.EYRIE] = 6
    state.eyrie.warriors_in_supply -= 6
    _assign_eyrie_leader_viziers(state, state.eyrie.leader)

    # Vagabond opening (forest abstracted as clearing 12 adjacency anchor)
    state.vagabond.location = 12


def _deal_opening_hands(state: GameState) -> None:
    for faction in [Faction.MARQUISE, Faction.EYRIE, Faction.VAGABOND]:
        opening_hand = [state.draw_pile.pop() for _ in range(3)]
        state.faction_state(faction).hand.extend(opening_hand)

    # Woodland Alliance starts with supporters, not cards in hand.
    state.alliance.supporters.extend(state.draw_pile.pop() for _ in range(3))


def _assign_eyrie_leader_viziers(state: GameState, leader: str) -> None:
    card_ids = _leader_vizier_card_ids()
    mapping = {
        "despot": ("move", "build"),
        "commander": ("move", "battle"),
        "charismatic": ("recruit", "battle"),
        "builder": ("recruit", "move"),
    }
    for cards in state.eyrie.decree.values():
        cards[:] = [card_id for card_id in cards if card_id > 0]
    for column in mapping[leader]:
        state.eyrie.decree[column].append(card_ids[column])


def _leader_vizier_card_ids() -> dict[str, int]:
    return {"recruit": -101, "move": -102, "battle": -103, "build": -104}
