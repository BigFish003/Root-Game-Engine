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
from ..enums import BuildingType, CardTag, DecisionType, Faction, Phase, Suit, TokenType
from ..models import GameState
from . import alliance as alliance_rules
from .combat import legal_battle_clearings, legal_battle_targets, resolve_basic_battle
from .crafting import legal_craft_cards, spend_marquise_crafting_power
from .movement import legal_move_destinations, legal_move_sources
from .rulership import rules_clearing


def valid_actions(state: GameState) -> list:
    """Return legal next actions for Marquise in current decision context."""

    if state.turn.phase != Phase.DAYLIGHT:
        return [EndPhase()]

    ctx = state.decision_context
    if ctx.decision_type == DecisionType.MAIN_ACTION:
        actions: list = [EndPhase()]
        if state.marquise.crafting_window_open:
            actions.extend(
                Craft(card_id) for card_id in legal_craft_cards(state, state.marquise.hand, Faction.MARQUISE)
            )
        if state.marquise.daylight_actions_used >= 3:
            return actions
        if not state.marquise.recruit_used_this_turn:
            actions.extend(Recruit(cid) for cid in _legal_recruit_clearings(state))
        actions.extend(
            Build(clearing_id=cid, building_type=b)
            for cid, b in _legal_builds(state)
        )
        actions.extend(SelectMoveSource(cid) for cid in legal_move_sources(state, Faction.MARQUISE))
        actions.extend(SelectBattleClearing(cid) for cid in legal_battle_clearings(state, Faction.MARQUISE))
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
    if state.turn.phase != Phase.DAYLIGHT:
        raise ValueError("Recruit can only be taken in Daylight")
    if state.marquise.recruit_used_this_turn:
        raise ValueError("Marquise recruit can only be used once per turn")
    if state.marquise.warriors_in_supply <= 0:
        raise ValueError("No Marquise warriors in supply")
    state.board.warriors[action.clearing_id][Faction.MARQUISE] += 1
    state.marquise.warriors_in_supply -= 1
    state.marquise.recruit_used_this_turn = True
    state.marquise.daylight_actions_used += 1
    state.marquise.crafting_window_open = False


def apply_build(state: GameState, action: Build) -> None:
    if state.turn.phase != Phase.DAYLIGHT:
        raise ValueError("Build can only be taken in Daylight")
    if not _marquise_rules_clearing(state, action.clearing_id):
        raise ValueError("Marquise must rule the clearing to build")
    if state.marquise.buildings_in_supply[action.building_type] <= 0:
        raise ValueError("No building of requested type left")
    if action.building_type not in [BuildingType.SAWMILL, BuildingType.WORKSHOP, BuildingType.RECRUITER]:
        raise ValueError("Marquise cannot build this building type")
    buildings = state.board.buildings[action.clearing_id][Faction.MARQUISE]
    slots = state.board.clearings[action.clearing_id].building_slots
    if len(buildings) >= slots:
        raise ValueError("No free building slot")
    wood_cost = _marquise_build_cost(state, action.building_type)
    if wood_cost > 0:
        paid = _pay_wood_cost(state, action.clearing_id, wood_cost)
        if not paid:
            raise ValueError("Not enough connected wood to pay build cost")
    buildings.append(action.building_type)
    state.marquise.buildings_in_supply[action.building_type] -= 1
    state.scores[Faction.MARQUISE] += _marquise_build_score(state, action.building_type)
    state.marquise.daylight_actions_used += 1
    state.marquise.crafting_window_open = False


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
    alliance_rules.trigger_outrage(state, Faction.MARQUISE, action.clearing_id)
    state.decision_context.decision_type = DecisionType.MAIN_ACTION
    state.decision_context.selected_source = None
    state.marquise.daylight_actions_used += 1
    state.marquise.crafting_window_open = False


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
    state.marquise.daylight_actions_used += 1
    state.marquise.crafting_window_open = False


def apply_craft(state: GameState, action: Craft) -> None:
    if state.turn.phase != Phase.DAYLIGHT:
        raise ValueError("Craft can only be taken in Daylight")
    if not state.marquise.crafting_window_open:
        raise ValueError("Crafting is only available at the start of Daylight")
    if action.card_id not in state.marquise.hand:
        raise ValueError("Card not in hand")
    if action.card_id not in legal_craft_cards(state, state.marquise.hand, Faction.MARQUISE):
        raise ValueError("Card cannot be crafted with available workshops")
    spend_marquise_crafting_power(state, action.card_id)
    card = state.cards[action.card_id]
    state.marquise.hand.remove(action.card_id)
    if card.vp_on_craft > 0:
        state.scores[Faction.MARQUISE] += card.vp_on_craft
    if card.name.startswith("Favor of the"):
        _resolve_favor(state, card.suit)
    if CardTag.PERSISTENT_EFFECT in card.tags:
        state.marquise.crafted_effects.append(card.name)
    else:
        state.discard_pile.append(action.card_id)


def _resolve_favor(state: GameState, favor_suit: Suit) -> None:
    for cid, clearing in state.board.clearings.items():
        if clearing.suit != favor_suit:
            continue
        state.board.warriors[cid][Faction.EYRIE] = 0
        state.board.warriors[cid][Faction.ALLIANCE] = 0
        state.board.buildings[cid][Faction.EYRIE].clear()
        state.board.buildings[cid][Faction.ALLIANCE].clear()
        sympathy_removed = sum(
            1 for token in state.board.tokens[cid][Faction.ALLIANCE] if token == TokenType.SYMPATHY
        )
        state.board.tokens[cid][Faction.ALLIANCE] = [
            token for token in state.board.tokens[cid][Faction.ALLIANCE] if token != TokenType.SYMPATHY
        ]
        for _ in range(sympathy_removed):
            alliance_rules.trigger_outrage(state, Faction.MARQUISE, cid, require_sympathy_present=False)


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
        if not _marquise_rules_clearing(state, cid):
            continue
        for btype in [BuildingType.SAWMILL, BuildingType.WORKSHOP, BuildingType.RECRUITER]:
            if (
                state.marquise.buildings_in_supply[btype] > 0
                and _has_build_payment(state, cid, _marquise_build_cost(state, btype))
            ):
                result.append((cid, btype))
    return result


def _marquise_build_cost(state: GameState, building_type: BuildingType) -> int:
    placed = 6 - state.marquise.buildings_in_supply[building_type]
    return [0, 1, 2, 3, 3, 4][placed]


def _marquise_build_score(state: GameState, building_type: BuildingType) -> int:
    placed = 6 - state.marquise.buildings_in_supply[building_type]
    return [0, 1, 2, 3, 4, 5][placed]


def _marquise_rules_clearing(state: GameState, clearing_id: int) -> bool:
    return rules_clearing(state, clearing_id, Faction.MARQUISE)


def _reachable_ruled_clearings(state: GameState, origin: int) -> set[int]:
    if not _marquise_rules_clearing(state, origin):
        return set()
    seen = {origin}
    stack = [origin]
    while stack:
        cid = stack.pop()
        for nxt in state.board.clearings[cid].adjacent_clearings:
            if nxt in seen:
                continue
            if not _marquise_rules_clearing(state, nxt):
                continue
            seen.add(nxt)
            stack.append(nxt)
    return seen


def _wood_count_in_clearing(state: GameState, clearing_id: int) -> int:
    return sum(1 for token in state.board.tokens[clearing_id][Faction.MARQUISE] if token == TokenType.WOOD)


def _has_build_payment(state: GameState, target_clearing: int, cost: int) -> bool:
    if cost <= 0:
        return True
    reachable = _reachable_ruled_clearings(state, target_clearing)
    available_wood = sum(_wood_count_in_clearing(state, cid) for cid in reachable)
    return available_wood >= cost


def _pay_wood_cost(state: GameState, target_clearing: int, cost: int) -> bool:
    if cost <= 0:
        return True
    reachable = sorted(_reachable_ruled_clearings(state, target_clearing))
    remaining = cost
    for cid in reachable:
        tokens = state.board.tokens[cid][Faction.MARQUISE]
        wood_indexes = [idx for idx, token in enumerate(tokens) if token == TokenType.WOOD]
        remove_now = min(len(wood_indexes), remaining)
        for token_idx in reversed(wood_indexes[:remove_now]):
            tokens.pop(token_idx)
        remaining -= remove_now
        if remaining == 0:
            return True
    return False
