"""Eyrie-specific legal action generation and application."""

from __future__ import annotations

from ..actions import (
    Build,
    Craft,
    EndDecision,
    EndPhase,
    Recruit,
    SelectBattleClearing,
    SelectBattleTarget,
    SelectMoveDestination,
    SelectMoveSource,
)
from ..enums import BuildingType, DecisionType, Faction, Phase
from ..models import GameState
from .combat import legal_battle_clearings, legal_battle_targets, resolve_basic_battle
from .crafting import legal_craft_cards
from .movement import legal_move_destinations, legal_move_sources


def valid_actions(state: GameState) -> list:
    if state.turn.phase != Phase.DAYLIGHT:
        return [EndPhase()]

    ctx = state.decision_context
    if ctx.decision_type == DecisionType.MAIN_ACTION:
        actions: list = [EndPhase()]
        actions.extend(Recruit(cid) for cid in _legal_recruit_clearings(state))
        actions.extend(Build(clearing_id=cid, building_type=BuildingType.ROOST) for cid in _legal_roost_builds(state))
        actions.extend(SelectMoveSource(cid) for cid in legal_move_sources(state, Faction.EYRIE))
        actions.extend(SelectBattleClearing(cid) for cid in legal_battle_clearings(state, Faction.EYRIE))
        actions.extend(Craft(card_id) for card_id in legal_craft_cards(state, state.eyrie.hand, Faction.EYRIE))
        return actions
    if ctx.decision_type == DecisionType.SELECT_MOVE_DESTINATION and ctx.selected_source is not None:
        return [SelectMoveDestination(cid) for cid in legal_move_destinations(state, ctx.selected_source)] + [EndDecision()]
    if ctx.decision_type == DecisionType.SELECT_BATTLE_TARGET and ctx.selected_battle_clearing is not None:
        return [
            SelectBattleTarget(f.value)
            for f in legal_battle_targets(state, Faction.EYRIE, ctx.selected_battle_clearing)
        ] + [EndDecision()]
    return [EndDecision()]


def apply_recruit(state: GameState, action: Recruit) -> None:
    if state.eyrie.warriors_in_supply <= 0:
        raise ValueError("No Eyrie warriors in supply")
    state.board.warriors[action.clearing_id][Faction.EYRIE] += 1
    state.eyrie.warriors_in_supply -= 1


def apply_build(state: GameState, action: Build) -> None:
    if action.building_type != BuildingType.ROOST:
        raise ValueError("Eyrie can only build roosts")
    if state.eyrie.roosts_in_supply <= 0:
        raise ValueError("No roosts left")
    if len(state.board.buildings[action.clearing_id][Faction.EYRIE]) >= state.board.clearings[action.clearing_id].building_slots:
        raise ValueError("No free slot")
    state.board.buildings[action.clearing_id][Faction.EYRIE].append(BuildingType.ROOST)
    state.eyrie.roosts_in_supply -= 1
    state.scores[Faction.EYRIE] += 1


def apply_move_source(state: GameState, action: SelectMoveSource) -> None:
    state.decision_context.decision_type = DecisionType.SELECT_MOVE_DESTINATION
    state.decision_context.selected_source = action.clearing_id


def apply_move_destination(state: GameState, action: SelectMoveDestination) -> None:
    source = state.decision_context.selected_source
    if source is None:
        raise ValueError("No source selected")
    if state.board.warriors[source][Faction.EYRIE] <= 0:
        raise ValueError("No Eyrie warrior at source")
    state.board.warriors[source][Faction.EYRIE] -= 1
    state.board.warriors[action.clearing_id][Faction.EYRIE] += 1
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
    resolve_basic_battle(state, Faction.EYRIE, target, clearing)
    state.decision_context.decision_type = DecisionType.MAIN_ACTION
    state.decision_context.selected_battle_clearing = None


def apply_craft(state: GameState, action: Craft) -> None:
    if action.card_id not in state.eyrie.hand:
        raise ValueError("Card not in hand")
    state.eyrie.hand.remove(action.card_id)
    state.discard_pile.append(action.card_id)


def _legal_recruit_clearings(state: GameState) -> list[int]:
    return [
        cid
        for cid, buildings in state.board.buildings.items()
        if any(b == BuildingType.ROOST for b in buildings[Faction.EYRIE])
    ]


def _legal_roost_builds(state: GameState) -> list[int]:
    result: list[int] = []
    for cid in state.board.clearings:
        if state.board.warriors[cid][Faction.EYRIE] <= 0:
            continue
        slots = state.board.clearings[cid].building_slots
        if len(state.board.buildings[cid][Faction.EYRIE]) < slots:
            result.append(cid)
    return result
