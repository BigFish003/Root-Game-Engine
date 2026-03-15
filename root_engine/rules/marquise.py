"""Marquise-specific legal action generation and application."""

from __future__ import annotations

from ..actions import (
    Build,
    Craft,
    EndDecision,
    EndPhase,
    Recruit,
    ResolveMove,
    SelectBattleClearing,
    SelectBattleTarget,
    SelectMoveDestination,
    SelectMoveSource,
)
from ..enums import BuildingType, DecisionType, Faction
from ..models import GameState
from .combat import legal_battle_clearings, legal_battle_targets, resolve_basic_battle
from .crafting import legal_craft_cards
from .movement import legal_move_destinations, legal_move_sources


def valid_actions(state: GameState) -> list:
    """Return legal next actions for Marquise in current decision context."""

    ctx = state.decision_context
    if ctx.decision_type == DecisionType.MAIN_ACTION:
        actions: list = [EndPhase()]
        actions.extend(Recruit(cid) for cid in _legal_recruit_clearings(state))
        actions.extend(
            Build(clearing_id=cid, building_type=b)
            for cid, b in _legal_builds(state)
        )
        actions.extend(SelectMoveSource(cid) for cid in legal_move_sources(state, Faction.MARQUISE))
        actions.extend(SelectBattleClearing(cid) for cid in legal_battle_clearings(state, Faction.MARQUISE))
        actions.extend(Craft(card_id) for card_id in legal_craft_cards(state, state.marquise.hand))
        return actions
    if ctx.decision_type == DecisionType.SELECT_MOVE_DESTINATION and ctx.selected_source is not None:
        return [SelectMoveDestination(cid) for cid in legal_move_destinations(state, ctx.selected_source)] + [EndDecision()]
    if ctx.decision_type == DecisionType.SELECT_BATTLE_TARGET and ctx.selected_battle_clearing is not None:
        return [
            SelectBattleTarget(f.value)
            for f in legal_battle_targets(state, Faction.MARQUISE, ctx.selected_battle_clearing)
        ] + [EndDecision()]
    return [EndDecision()]


def apply_recruit(state: GameState, action: Recruit) -> None:
    if state.marquise.warriors_in_supply <= 0:
        raise ValueError("No Marquise warriors in supply")
    state.board.warriors[action.clearing_id][Faction.MARQUISE] += 1
    state.marquise.warriors_in_supply -= 1


def apply_build(state: GameState, action: Build) -> None:
    if state.marquise.buildings_in_supply[action.building_type] <= 0:
        raise ValueError("No building of requested type left")
    if action.building_type not in [BuildingType.SAWMILL, BuildingType.WORKSHOP, BuildingType.RECRUITER]:
        raise ValueError("Marquise cannot build this building type")
    buildings = state.board.buildings[action.clearing_id][Faction.MARQUISE]
    slots = state.board.clearings[action.clearing_id].building_slots
    if len(buildings) >= slots:
        raise ValueError("No free building slot")
    buildings.append(action.building_type)
    state.marquise.buildings_in_supply[action.building_type] -= 1
    state.scores[Faction.MARQUISE] += 1


def apply_move_source(state: GameState, action: SelectMoveSource) -> None:
    state.decision_context.decision_type = DecisionType.SELECT_MOVE_DESTINATION
    state.decision_context.selected_source = action.clearing_id


def apply_move_destination(state: GameState, action: SelectMoveDestination) -> None:
    source = state.decision_context.selected_source
    if source is None:
        raise ValueError("No selected source for move")
    if state.board.warriors[source][Faction.MARQUISE] <= 0:
        raise ValueError("No Marquise warrior at source")
    state.board.warriors[source][Faction.MARQUISE] -= 1
    state.board.warriors[action.clearing_id][Faction.MARQUISE] += 1
    state.decision_context.decision_type = DecisionType.MAIN_ACTION
    state.decision_context.selected_source = None


def apply_battle_select_clearing(state: GameState, action: SelectBattleClearing) -> None:
    state.decision_context.decision_type = DecisionType.SELECT_BATTLE_TARGET
    state.decision_context.selected_battle_clearing = action.clearing_id


def apply_battle_select_target(state: GameState, action: SelectBattleTarget) -> None:
    clearing = state.decision_context.selected_battle_clearing
    if clearing is None:
        raise ValueError("No battle clearing selected")
    target = Faction(action.target_faction)
    resolve_basic_battle(state, Faction.MARQUISE, target, clearing)
    state.decision_context.decision_type = DecisionType.MAIN_ACTION
    state.decision_context.selected_battle_clearing = None


def apply_craft(state: GameState, action: Craft) -> None:
    if action.card_id not in state.marquise.hand:
        raise ValueError("Card not in hand")
    state.marquise.hand.remove(action.card_id)
    state.discard_pile.append(action.card_id)


def _legal_recruit_clearings(state: GameState) -> list[int]:
    return [
        cid
        for cid, buildings in state.board.buildings.items()
        if any(b == BuildingType.RECRUITER for b in buildings[Faction.MARQUISE])
    ]


def _legal_builds(state: GameState) -> list[tuple[int, BuildingType]]:
    result: list[tuple[int, BuildingType]] = []
    for cid in state.board.clearings:
        if state.board.warriors[cid][Faction.MARQUISE] <= 0:
            continue
        existing = state.board.buildings[cid][Faction.MARQUISE]
        slots = state.board.clearings[cid].building_slots
        if len(existing) >= slots:
            continue
        for btype in [BuildingType.SAWMILL, BuildingType.WORKSHOP, BuildingType.RECRUITER]:
            if state.marquise.buildings_in_supply[btype] > 0:
                result.append((cid, btype))
    return result
