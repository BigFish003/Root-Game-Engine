"""Player-specific observation models and builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import Faction, Suit
from .models import GameState


@dataclass(frozen=True)
class ObservedClearing:
    """Public board information visible to all factions for one clearing."""

    clearing_id: int
    suit: Suit
    adjacent_clearings: list[int]
    warriors: dict[Faction, int]
    buildings: dict[Faction, list[str]]
    tokens: dict[Faction, list[str]]
    ruler: Faction | None


@dataclass(frozen=True)
class ObservedFactionBoard:
    """Public and optional private data for a faction board."""

    faction: Faction
    score: int
    hand_count: int
    hand: list[int] | None
    crafted_effects: list[str]
    public_data: dict[str, Any] = field(default_factory=dict)
    private_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Observation:
    """Filtered state view for a specific requesting faction."""

    observer: Faction
    clearings: dict[int, ObservedClearing]
    scores: dict[Faction, int]
    discard_pile: list[int]
    current_faction: Faction
    current_phase: str
    round_number: int
    decision: dict[str, Any]
    factions: dict[Faction, ObservedFactionBoard]


def build_observation(state: GameState, observer: Faction) -> Observation:
    """Build a player-specific observation from full game state."""

    clearings = {
        cid: ObservedClearing(
            clearing_id=cid,
            suit=clearing.suit,
            adjacent_clearings=list(clearing.adjacent_clearings),
            warriors=dict(state.board.warriors[cid]),
            buildings={f: [b.value for b in bl] for f, bl in state.board.buildings[cid].items()},
            tokens={f: [t.value for t in tl] for f, tl in state.board.tokens[cid].items()},
            ruler=_determine_ruler(state, cid),
        )
        for cid, clearing in state.board.clearings.items()
    }

    faction_views: dict[Faction, ObservedFactionBoard] = {}
    for faction in Faction:
        faction_state = state.faction_state(faction)
        hand = list(faction_state.hand) if faction == observer else None
        faction_views[faction] = ObservedFactionBoard(
            faction=faction,
            score=state.scores[faction],
            hand_count=len(faction_state.hand),
            hand=hand,
            crafted_effects=list(faction_state.crafted_effects),
            public_data=_public_faction_data(state, faction),
            private_data=_private_faction_data(state, faction, observer),
        )

    return Observation(
        observer=observer,
        clearings=clearings,
        scores=dict(state.scores),
        discard_pile=list(state.discard_pile),
        current_faction=state.turn.current_faction,
        current_phase=state.turn.phase.value,
        round_number=state.turn.round_number,
        decision={
            "decision_type": state.decision_context.decision_type.value,
            "selected_source": state.decision_context.selected_source,
            "selected_destination": state.decision_context.selected_destination,
            "selected_battle_clearing": state.decision_context.selected_battle_clearing,
        },
        factions=faction_views,
    )


def _determine_ruler(state: GameState, clearing_id: int) -> Faction | None:
    rule_counts = {
        faction: state.board.warriors[clearing_id][faction] + len(state.board.buildings[clearing_id][faction])
        for faction in [Faction.MARQUISE, Faction.EYRIE, Faction.ALLIANCE]
    }
    top = max(rule_counts.values())
    if top == 0:
        return None
    leaders = [f for f, count in rule_counts.items() if count == top]
    return leaders[0] if len(leaders) == 1 else None


def _public_faction_data(state: GameState, faction: Faction) -> dict[str, Any]:
    if faction == Faction.MARQUISE:
        return {
            "warriors_in_supply": state.marquise.warriors_in_supply,
            "buildings_in_supply": {k.value: v for k, v in state.marquise.buildings_in_supply.items()},
            "keep_clearing": state.marquise.keep_clearing,
            "wood_tokens_on_map": _count_tokens_on_map(state, faction, "wood"),
        }
    if faction == Faction.EYRIE:
        return {
            "warriors_in_supply": state.eyrie.warriors_in_supply,
            "roosts_in_supply": state.eyrie.roosts_in_supply,
            "leader": state.eyrie.leader,
            "decree": {k: list(v) for k, v in state.eyrie.decree.items()},
        }
    if faction == Faction.ALLIANCE:
        return {
            "officers": state.alliance.officers,
            "bases": {k.value: v for k, v in state.alliance.bases.items()},
            "sympathy_in_supply": state.alliance.sympathy_in_supply,
            "supporters_hidden": True,
        }
    return {
        "location": state.vagabond.location,
        "satchel": {k.value: v for k, v in state.vagabond.satchel.items()},
        "exhausted_items": {k.value: v for k, v in state.vagabond.exhausted_items.items()},
        "damaged_items": {k.value: v for k, v in state.vagabond.damaged_items.items()},
        "relationships": {k.value: v.value for k, v in state.vagabond.relationships.items()},
    }


def _private_faction_data(state: GameState, faction: Faction, observer: Faction) -> dict[str, Any]:
    if faction != observer:
        return {}
    if faction == Faction.ALLIANCE:
        return {"supporters": list(state.alliance.supporters)}
    return {}


def _count_tokens_on_map(state: GameState, faction: Faction, token_name: str) -> int:
    total = 0
    for cid in state.board.clearings:
        total += sum(1 for t in state.board.tokens[cid][faction] if t.value == token_name)
    return total
