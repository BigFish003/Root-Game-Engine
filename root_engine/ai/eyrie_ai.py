"""Eyrie AI policy utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..actions import (
    AddToDecree,
    Build,
    Craft,
    EndPhase,
    FallIntoTurmoil,
    Recruit,
    SelectBattleClearing,
    SelectBattleTarget,
    SelectEyrieLeader,
    SelectMoveDestination,
    SelectMoveSource,
)
from ..enums import BuildingType, Faction, Phase, Suit


@dataclass(frozen=True)
class SearchConfig:
    max_depth: int = 2
    branch_factor: int = 16


def choose_action(engine: Any, config: SearchConfig) -> Any:
    state = engine.get_state()
    if state.turn.current_faction != Faction.EYRIE:
        raise ValueError("choose_action called outside Eyrie turn")

    valid_actions = engine.get_valid_actions()
    if len(valid_actions) == 1:
        return valid_actions[0]

    best_score = float("-inf")
    best_action = valid_actions[0]
    for action in valid_actions[: config.branch_factor]:
        sim = engine.clone()
        sim._marquise_ai_enabled = False
        sim._eyrie_ai_enabled = False
        sim.apply_action(action)
        score = _search(sim, config.max_depth - 1, config.branch_factor)
        score += _action_bias(action, state)
        if score > best_score:
            best_score = score
            best_action = action
    return best_action


def _search(engine: Any, depth: int, branch_factor: int) -> float:
    state = engine.get_state()
    if depth <= 0 or state.turn.current_faction != Faction.EYRIE or engine.is_terminal():
        return _evaluate_position(state)

    actions = engine.get_valid_actions()
    if not actions:
        return _evaluate_position(state)

    best = float("-inf")
    for action in actions[:branch_factor]:
        sim = engine.clone()
        sim._marquise_ai_enabled = False
        sim._eyrie_ai_enabled = False
        sim.apply_action(action)
        score = _search(sim, depth - 1, branch_factor) + _action_bias(action, state)
        best = max(best, score)
    return best


def _evaluate_position(state: Any) -> float:
    eyrie = state.eyrie
    score = float(state.scores[Faction.EYRIE] * 130)

    roosts = 0
    eyrie_warriors = 0
    enemy_presence = 0
    decree_cards = 0
    bird_cards = 0

    for cid in state.board.clearings:
        eyrie_warriors += state.board.warriors[cid].get(Faction.EYRIE, 0)
        enemy_presence += (
            state.board.warriors[cid].get(Faction.MARQUISE, 0)
            + state.board.warriors[cid].get(Faction.ALLIANCE, 0)
        )
        roosts += sum(1 for b in state.board.buildings[cid].get(Faction.EYRIE, []) if b == BuildingType.ROOST)

    for cards in eyrie.decree.values():
        decree_cards += len(cards)
        bird_cards += sum(1 for card_id in cards if card_id < 0 or state.cards[card_id].suit == Suit.BIRD)

    score += roosts * 30
    score += eyrie_warriors * 3.2
    score += decree_cards * 3.0
    score += bird_cards * 2.0
    score += len(eyrie.hand) * 1.2
    score += (7 - eyrie.roosts_in_supply) * 8
    if eyrie.pending_leader_selection:
        score -= 120
    if state.turn.phase == Phase.EVENING:
        score += 10
    score -= max(0, enemy_presence - eyrie_warriors) * 1.5
    return score


def _action_bias(action: Any, state: Any) -> float:
    if isinstance(action, SelectEyrieLeader): return 30
    if isinstance(action, Build): return 24
    if isinstance(action, Recruit): return 16
    if isinstance(action, SelectBattleClearing): return 13
    if isinstance(action, SelectBattleTarget): return 12
    if isinstance(action, SelectMoveSource): return 9
    if isinstance(action, SelectMoveDestination): return 8
    if isinstance(action, AddToDecree):
        return 7 + _decree_add_bias(action, state)
    if isinstance(action, Craft): return 6
    if isinstance(action, EndPhase): return -14
    if isinstance(action, FallIntoTurmoil): return -40
    return 0


def _decree_add_bias(action: AddToDecree, state: Any) -> float:
    eyrie = state.eyrie
    card_suit = Suit.BIRD if action.card_id < 0 else state.cards[action.card_id].suit
    open_roosts = sum(
        state.board.clearings[cid].building_slots - len(state.board.buildings[cid][Faction.EYRIE])
        for cid in state.board.clearings
        if state.board.warriors[cid][Faction.EYRIE] > 0
    )
    legal_battles = sum(
        1
        for cid in state.board.clearings
        if state.board.warriors[cid][Faction.EYRIE] > 0
        and (
            state.board.warriors[cid].get(Faction.MARQUISE, 0) > 0
            or state.board.warriors[cid].get(Faction.ALLIANCE, 0) > 0
        )
    )
    legal_moves = sum(
        1
        for cid in state.board.clearings
        if state.board.warriors[cid][Faction.EYRIE] > 0
        and any(
            state.board.clearings[nid].suit is not None
            for nid in state.board.clearings[cid].adjacent_clearings
        )
    )
    roost_count = 7 - eyrie.roosts_in_supply
    can_recruit = roost_count > 0 and eyrie.warriors_in_supply > 0

    decree_size = len(eyrie.decree[action.column])
    risk_penalty = decree_size * 2.2
    if card_suit == Suit.BIRD:
        risk_penalty += 3.5 + decree_size * 1.5

    fit_bonus = 0.0
    if action.column == "build":
        fit_bonus += min(12.0, open_roosts * 3.0)
    elif action.column == "battle":
        fit_bonus += min(11.0, legal_battles * 3.0)
    elif action.column == "move":
        expansion_need = max(0, 5 - roost_count)
        fit_bonus += min(10.0, legal_moves * 1.8 + expansion_need * 1.7)
    elif action.column == "recruit":
        if can_recruit:
            fit_bonus += min(10.0, eyrie.warriors_in_supply * 0.6)
        else:
            fit_bonus -= 8.0

    if action.column == "build" and open_roosts <= 0:
        fit_bonus -= 10.0
    if action.column == "battle" and legal_battles <= 0:
        fit_bonus -= 9.0
    if action.column == "move" and legal_moves <= 0:
        fit_bonus -= 8.0

    suit_match_potential = _column_suit_match_count(state, action.column, card_suit)
    fit_bonus += min(7.0, suit_match_potential * 1.4)

    return fit_bonus - risk_penalty


def _column_suit_match_count(state: Any, column: str, card_suit: Suit) -> int:
    if card_suit == Suit.BIRD:
        return 3

    if column == "recruit":
        return sum(
            1
            for cid in state.board.clearings
            if any(b == BuildingType.ROOST for b in state.board.buildings[cid][Faction.EYRIE])
            and state.board.clearings[cid].suit == card_suit
        )
    if column == "build":
        return sum(
            1
            for cid in state.board.clearings
            if state.board.warriors[cid][Faction.EYRIE] > 0
            and len(state.board.buildings[cid][Faction.EYRIE]) < state.board.clearings[cid].building_slots
            and state.board.clearings[cid].suit == card_suit
        )

    if column == "battle":
        return sum(
            1
            for cid in state.board.clearings
            if state.board.warriors[cid][Faction.EYRIE] > 0
            and state.board.clearings[cid].suit == card_suit
            and (
                state.board.warriors[cid].get(Faction.MARQUISE, 0) > 0
                or state.board.warriors[cid].get(Faction.ALLIANCE, 0) > 0
            )
        )

    return sum(
        1
        for cid in state.board.clearings
        if state.board.warriors[cid][Faction.EYRIE] > 0
        and state.board.clearings[cid].suit == card_suit
    )
