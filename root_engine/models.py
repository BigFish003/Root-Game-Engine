"""Typed data models for cards, map and faction states."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .enums import (
    BuildingType,
    CardTag,
    DecisionType,
    Faction,
    ItemType,
    Phase,
    Suit,
    TokenType,
    VagabondRelation,
)


@dataclass(frozen=True)
class Card:
    """A single card in the deck."""

    card_id: int
    name: str
    suit: Suit
    tags: tuple[CardTag, ...] = ()
    craft_cost: dict[Suit, int] = field(default_factory=dict)
    craft_cost_any: int = 0
    craftable: bool = True
    vp_on_craft: int = 0


@dataclass
class Clearing:
    """Board clearing definition and mutable occupancy state."""

    clearing_id: int
    suit: Suit
    building_slots: int
    adjacent_clearings: list[int]
    adjacent_forests: list[int] = field(default_factory=list)
    has_ruin: bool = False


@dataclass
class BoardState:
    """Piece placement data keyed by clearing and faction."""

    clearings: dict[int, Clearing]
    warriors: dict[int, dict[Faction, int]] = field(default_factory=dict)
    buildings: dict[int, dict[Faction, list[BuildingType]]] = field(default_factory=dict)
    tokens: dict[int, dict[Faction, list[TokenType]]] = field(default_factory=dict)


@dataclass
class DecisionContext:
    """Tracks partial selections for compound actions."""

    decision_type: DecisionType = DecisionType.MAIN_ACTION
    selected_source: Optional[int] = None
    selected_destination: Optional[int] = None
    selected_battle_clearing: Optional[int] = None
    pending_moves_remaining: int = 0


@dataclass
class MarquiseState:
    warriors_in_supply: int = 25
    buildings_in_supply: dict[BuildingType, int] = field(
        default_factory=lambda: {
            BuildingType.SAWMILL: 6,
            BuildingType.WORKSHOP: 6,
            BuildingType.RECRUITER: 6,
        }
    )
    keep_clearing: Optional[int] = None
    hand: list[int] = field(default_factory=list)
    crafted_effects: list[str] = field(default_factory=list)
    daylight_actions_used: int = 0
    recruit_used_this_turn: bool = False
    crafting_power: dict[Suit, int] = field(
        default_factory=lambda: {Suit.FOX: 0, Suit.RABBIT: 0, Suit.MOUSE: 0}
    )
    crafting_window_open: bool = False


@dataclass
class EyrieState:
    warriors_in_supply: int = 20
    roosts_in_supply: int = 7
    leader: str = "charismatic"
    decree: dict[str, list[int]] = field(
        default_factory=lambda: {"recruit": [], "move": [], "battle": [], "build": []}
    )
    hand: list[int] = field(default_factory=list)
    crafted_effects: list[str] = field(default_factory=list)
    crafting_window_open: bool = False
    resolving_decree: bool = False
    decree_column_index: int = 0
    decree_cards_remaining: dict[str, list[int]] = field(
        default_factory=lambda: {"recruit": [], "move": [], "battle": [], "build": []}
    )
    birdsong_cards_added: int = 0
    pending_leader_selection: bool = False
    turmoiled_leaders: list[str] = field(default_factory=list)


@dataclass
class AllianceState:
    supporters: list[int] = field(default_factory=list)
    officers: int = 0
    bases: dict[Suit, bool] = field(
        default_factory=lambda: {Suit.FOX: False, Suit.RABBIT: False, Suit.MOUSE: False}
    )
    sympathy_in_supply: int = 10
    hand: list[int] = field(default_factory=list)
    crafted_effects: list[str] = field(default_factory=list)
    military_ops_used: int = 0
    crafting_window_open: bool = False


@dataclass
class VagabondState:
    location: Optional[int] = None
    satchel: dict[ItemType, int] = field(default_factory=dict)
    exhausted_items: dict[ItemType, int] = field(default_factory=dict)
    damaged_items: dict[ItemType, int] = field(default_factory=dict)
    relationships: dict[Faction, VagabondRelation] = field(
        default_factory=lambda: {
            Faction.MARQUISE: VagabondRelation.INDIFFERENT,
            Faction.EYRIE: VagabondRelation.INDIFFERENT,
            Faction.ALLIANCE: VagabondRelation.INDIFFERENT,
        }
    )
    quests_completed: list[str] = field(default_factory=list)
    hand: list[int] = field(default_factory=list)
    crafted_effects: list[str] = field(default_factory=list)


@dataclass
class TurnState:
    current_faction: Faction = Faction.MARQUISE
    turn_order: list[Faction] = field(
        default_factory=lambda: [
            Faction.MARQUISE,
            Faction.EYRIE,
            Faction.ALLIANCE,
            Faction.VAGABOND,
        ]
    )
    phase: Phase = Phase.BIRDSONG
    round_number: int = 1


FactionState = MarquiseState | EyrieState | AllianceState | VagabondState


@dataclass
class GameState:
    """Canonical game state container."""

    seed: Optional[int]
    board: BoardState
    cards: dict[int, Card]
    draw_pile: list[int]
    discard_pile: list[int]
    scores: dict[Faction, int]
    dominance_holder: Optional[Faction]
    marquise: MarquiseState
    eyrie: EyrieState
    alliance: AllianceState
    vagabond: VagabondState
    turn: TurnState
    decision_context: DecisionContext
    pending_interrupts: list[str] = field(default_factory=list)

    def faction_state(self, faction: Faction) -> FactionState:
        if faction == Faction.MARQUISE:
            return self.marquise
        if faction == Faction.EYRIE:
            return self.eyrie
        if faction == Faction.ALLIANCE:
            return self.alliance
        return self.vagabond
