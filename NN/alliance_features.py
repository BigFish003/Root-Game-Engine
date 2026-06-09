from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import torch

from root_engine.enums import (
    BuildingType,
    DecisionType,
    Faction,
    ItemType,
    Phase,
    Suit,
    TokenType,
    VagabondRelation,
)
from root_engine.observation import Observation


CLEARING_IDS: tuple[int, ...] = tuple(range(1, 13))
FOREST_IDS: tuple[int, ...] = tuple(range(1, 9))
CARD_IDS: tuple[int, ...] = tuple(range(1, 55))
VIZIER_CARD_IDS: tuple[int, ...] = (-101, -102, -103, -104)
VISIBLE_CARD_IDS: tuple[int, ...] = CARD_IDS + VIZIER_CARD_IDS
FACTION_ORDER: tuple[Faction, ...] = (
    Faction.MARQUISE,
    Faction.EYRIE,
    Faction.ALLIANCE,
    Faction.VAGABOND,
)
SUIT_ORDER: tuple[Suit, ...] = (Suit.FOX, Suit.RABBIT, Suit.MOUSE, Suit.BIRD)
CLEARING_SUIT_ORDER: tuple[Suit, ...] = (Suit.FOX, Suit.RABBIT, Suit.MOUSE)
PHASE_ORDER: tuple[Phase, ...] = (Phase.BIRDSONG, Phase.DAYLIGHT, Phase.EVENING)
DECISION_ORDER: tuple[DecisionType, ...] = tuple(DecisionType)
BUILDING_ORDER: tuple[BuildingType, ...] = (
    BuildingType.SAWMILL,
    BuildingType.WORKSHOP,
    BuildingType.RECRUITER,
    BuildingType.ROOST,
    BuildingType.BASE,
)
TOKEN_ORDER: tuple[TokenType, ...] = (TokenType.WOOD, TokenType.KEEP, TokenType.SYMPATHY)
RELATION_ORDER: tuple[VagabondRelation, ...] = tuple(VagabondRelation)
ITEM_ORDER: tuple[ItemType, ...] = tuple(ItemType)
EYRIE_LEADERS: tuple[str, ...] = ("despot", "commander", "charismatic", "builder")
EYRIE_DECREE_COLUMNS: tuple[str, ...] = ("recruit", "move", "battle", "build")

MAX_SCORE = 30
MAX_ROUND = 20
MAX_HAND_COUNT = 54
MAX_WARRIORS_IN_CLEARING = 25
MAX_BUILDINGS_IN_CLEARING = 3
MAX_TOKENS_IN_CLEARING = 12
MAX_BUILDING_SLOTS = 3
MAX_SUPPLY_COUNT = 25
MAX_ALLIANCE_OFFICERS = 10
MAX_ALLIANCE_SYMPATHY_SUPPLY = 10
MAX_VAGABOND_ITEM_COUNT = 8
MAX_DECREE_CARDS_PER_COLUMN = 20


class _FeatureBuilder:
    def __init__(self) -> None:
        self.features: list[float] = []

    def bool(self, value: bool) -> None:
        self.features.append(1.0 if value else 0.0)

    def one_hot(self, value: Any, choices: Sequence[Any], *, include_unknown: bool = False) -> None:
        matched = False
        for choice in choices:
            is_match = value == choice
            self.bool(is_match)
            matched = matched or is_match
        if include_unknown:
            self.bool(not matched)

    def one_hot_count(self, value: int | None, maximum: int) -> None:
        clipped = max(0, min(int(value or 0), maximum))
        for bucket in range(maximum + 1):
            self.bool(clipped == bucket)

    def one_hot_optional_clearing(self, clearing_id: int | None) -> None:
        self.one_hot(clearing_id, CLEARING_IDS, include_unknown=True)

    def multi_hot_cards(self, card_ids: Sequence[int] | None) -> None:
        visible = set(card_ids or [])
        for card_id in VISIBLE_CARD_IDS:
            self.bool(card_id in visible)

    def multi_hot_strings(self, values: Sequence[str], choices: Sequence[str]) -> None:
        visible = set(values)
        for choice in choices:
            self.bool(choice in visible)


def encode_observation(
    obs: Observation,
    *,
    observer: Faction = Faction.ALLIANCE,
    device: torch.device | None = None,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Flatten an `Observation` into one fixed-width Alliance-visible vector.

    The layout favors one-hot and multi-hot fields so categorical state is not
    compressed into arbitrary ordinals. Public state is encoded for every faction;
    private card identity vectors are only populated from the observer-visible hand
    and, for the Alliance observer, its private supporters.
    """

    builder = _FeatureBuilder()

    _encode_turn_context(builder, obs)
    _encode_scores(builder, obs)
    _encode_item_supply(builder, obs)
    _encode_decision_context(builder, obs)
    _encode_clearings(builder, obs)
    _encode_faction_boards(builder, obs, observer)
    _encode_visible_card_zones(builder, obs, observer)

    return torch.tensor(builder.features, dtype=dtype, device=device)


def _encode_turn_context(builder: _FeatureBuilder, obs: Observation) -> None:
    builder.one_hot(obs.current_faction, FACTION_ORDER)
    phase = _enum_or_none(Phase, obs.current_phase)
    builder.one_hot(phase, PHASE_ORDER, include_unknown=True)
    builder.one_hot_count(obs.round_number, MAX_ROUND)


def _encode_scores(builder: _FeatureBuilder, obs: Observation) -> None:
    for faction in FACTION_ORDER:
        builder.one_hot_count(obs.scores.get(faction, 0), MAX_SCORE)


def _encode_item_supply(builder: _FeatureBuilder, obs: Observation) -> None:
    for item_type in ITEM_ORDER:
        builder.one_hot_count(
            obs.item_supply.get(item_type.value, 0),
            MAX_VAGABOND_ITEM_COUNT,
        )


def _encode_decision_context(builder: _FeatureBuilder, obs: Observation) -> None:
    decision_type = _enum_or_none(DecisionType, obs.decision.get("decision_type"))
    builder.one_hot(decision_type, DECISION_ORDER, include_unknown=True)
    builder.one_hot_optional_clearing(obs.decision.get("selected_source"))
    builder.one_hot_optional_clearing(obs.decision.get("selected_destination"))
    builder.one_hot_optional_clearing(obs.decision.get("selected_battle_clearing"))


def _encode_clearings(builder: _FeatureBuilder, obs: Observation) -> None:
    for clearing_id in CLEARING_IDS:
        clearing = obs.clearings[clearing_id]
        builder.one_hot(clearing.suit, CLEARING_SUIT_ORDER)
        builder.one_hot_count(clearing.building_slots, MAX_BUILDING_SLOTS)
        for adjacent_id in CLEARING_IDS:
            builder.bool(adjacent_id in clearing.adjacent_clearings)
        for forest_id in FOREST_IDS:
            builder.bool(forest_id in clearing.adjacent_forests)
        builder.one_hot(clearing.ruler, FACTION_ORDER, include_unknown=True)

        for faction in FACTION_ORDER:
            builder.one_hot_count(clearing.warriors.get(faction, 0), MAX_WARRIORS_IN_CLEARING)

        for faction in FACTION_ORDER:
            buildings = clearing.buildings.get(faction, [])
            for building_type in BUILDING_ORDER:
                count = _count_values(buildings, building_type.value)
                builder.one_hot_count(count, MAX_BUILDINGS_IN_CLEARING)

        for faction in FACTION_ORDER:
            tokens = clearing.tokens.get(faction, [])
            for token_type in TOKEN_ORDER:
                count = _count_values(tokens, token_type.value)
                builder.one_hot_count(count, MAX_TOKENS_IN_CLEARING)


def _encode_faction_boards(builder: _FeatureBuilder, obs: Observation, observer: Faction) -> None:
    for faction in FACTION_ORDER:
        board = obs.factions[faction]
        builder.one_hot_count(board.hand_count, MAX_HAND_COUNT)
        builder.multi_hot_cards(board.hand if faction == observer else [])
        _encode_crafted_effects(builder, board.crafted_effects)
        builder.multi_hot_cards(board.crafted_cards)
        for item_type in ITEM_ORDER:
            builder.one_hot_count(
                board.crafted_items.get(item_type.value, 0),
                MAX_VAGABOND_ITEM_COUNT,
            )

        if faction == Faction.MARQUISE:
            _encode_marquise_public(builder, board.public_data)
        elif faction == Faction.EYRIE:
            _encode_eyrie_public(builder, board.public_data)
        elif faction == Faction.ALLIANCE:
            _encode_alliance_public(builder, board.public_data)
            _encode_alliance_private(builder, board.private_data, observer)
        else:
            _encode_vagabond_public(builder, board.public_data)


def _encode_marquise_public(builder: _FeatureBuilder, public: Mapping[str, Any]) -> None:
    builder.one_hot_count(public.get("warriors_in_supply"), MAX_SUPPLY_COUNT)
    supplies = public.get("buildings_in_supply", {})
    for building_type in (BuildingType.SAWMILL, BuildingType.WORKSHOP, BuildingType.RECRUITER):
        builder.one_hot_count(supplies.get(building_type.value, 0), 6)
    builder.one_hot_optional_clearing(public.get("keep_clearing"))
    builder.one_hot_count(public.get("wood_tokens_on_map"), MAX_TOKENS_IN_CLEARING)


def _encode_eyrie_public(builder: _FeatureBuilder, public: Mapping[str, Any]) -> None:
    builder.one_hot_count(public.get("warriors_in_supply"), 20)
    builder.one_hot_count(public.get("roosts_in_supply"), 7)
    builder.one_hot(public.get("leader"), EYRIE_LEADERS, include_unknown=True)
    decree = public.get("decree", {})
    decree_suits = public.get("decree_suits", {})
    for column in EYRIE_DECREE_COLUMNS:
        cards = decree.get(column, [])
        suits = [_enum_or_none(Suit, suit) for suit in decree_suits.get(column, [])]
        builder.multi_hot_cards(cards)
        builder.one_hot_count(len(cards), MAX_DECREE_CARDS_PER_COLUMN)
        for suit in SUIT_ORDER:
            matching_suit_count = sum(1 for card_suit in suits if card_suit == suit)
            builder.one_hot_count(matching_suit_count, MAX_DECREE_CARDS_PER_COLUMN)


def _encode_alliance_public(builder: _FeatureBuilder, public: Mapping[str, Any]) -> None:
    builder.one_hot_count(public.get("warriors_in_supply"), 10)
    builder.one_hot_count(public.get("officers"), MAX_ALLIANCE_OFFICERS)
    bases = public.get("bases", {})
    bases_in_supply = public.get("bases_in_supply", {})
    for suit in CLEARING_SUIT_ORDER:
        builder.bool(bool(bases.get(suit.value, False)))
    for suit in CLEARING_SUIT_ORDER:
        builder.bool(bool(bases_in_supply.get(suit.value, False)))
    builder.one_hot_count(public.get("sympathy_in_supply"), MAX_ALLIANCE_SYMPATHY_SUPPLY)
    builder.bool(bool(public.get("supporters_hidden", False)))


def _encode_alliance_private(builder: _FeatureBuilder, private: Mapping[str, Any], observer: Faction) -> None:
    supporters = private.get("supporters", []) if observer == Faction.ALLIANCE else []
    supporter_suits_by_id = private.get("supporter_suits_by_id", {}) if observer == Faction.ALLIANCE else {}
    supporter_suits = [_enum_or_none(Suit, suit) for suit in supporter_suits_by_id.values()]
    builder.multi_hot_cards(supporters)
    builder.one_hot_count(len(supporters), MAX_HAND_COUNT)
    for suit in SUIT_ORDER:
        matching_suit_count = sum(1 for supporter_suit in supporter_suits if supporter_suit == suit)
        builder.one_hot_count(matching_suit_count, MAX_HAND_COUNT)


def _encode_vagabond_public(builder: _FeatureBuilder, public: Mapping[str, Any]) -> None:
    builder.one_hot_optional_clearing(public.get("location"))
    builder.one_hot(public.get("forest_location"), FOREST_IDS, include_unknown=True)
    for key in ("satchel", "tracks", "exhausted_items", "exhausted_tracks", "damaged_items"):
        items = public.get(key, {})
        for item_type in ITEM_ORDER:
            builder.one_hot_count(items.get(item_type.value, 0), MAX_VAGABOND_ITEM_COUNT)
    relationships = public.get("relationships", {})
    for faction in (Faction.MARQUISE, Faction.EYRIE, Faction.ALLIANCE):
        relation = _enum_or_none(VagabondRelation, relationships.get(faction.value))
        builder.one_hot(relation, RELATION_ORDER, include_unknown=True)


def _encode_crafted_effects(builder: _FeatureBuilder, crafted_effects: Sequence[str]) -> None:
    persistent_effect_names = (
        "Armorers",
        "Sappers",
        "Brutal Tactics",
        "Royal Claim",
        "Better Burrow Bank",
        "Cobbler",
        "Command Warren",
        "Codebreakers",
        "Scouting Party",
        "Stand and Deliver!",
        "Tax Collector",
    )
    builder.multi_hot_strings(crafted_effects, persistent_effect_names)


def _encode_visible_card_zones(builder: _FeatureBuilder, obs: Observation, observer: Faction) -> None:
    builder.multi_hot_cards(obs.discard_pile)
    builder.one_hot_count(len(obs.discard_pile), MAX_HAND_COUNT)

    observer_board = obs.factions[observer]
    visible_hand = observer_board.hand or []
    builder.one_hot_count(len(visible_hand), MAX_HAND_COUNT)
    builder.multi_hot_cards(visible_hand)

    if observer == Faction.ALLIANCE:
        supporters = obs.factions[Faction.ALLIANCE].private_data.get("supporters", [])
        builder.one_hot_count(len(supporters), MAX_HAND_COUNT)
        builder.multi_hot_cards(supporters)
    else:
        builder.one_hot_count(0, MAX_HAND_COUNT)
        builder.multi_hot_cards([])


def _count_values(values: Sequence[str], target: str) -> int:
    return sum(1 for value in values if value == target)


def _enum_or_none(enum_type: type[Any], value: Any) -> Any | None:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (TypeError, ValueError):
        return None
