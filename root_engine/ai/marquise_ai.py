"""Marquise AI policy utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..actions import Build, Craft, EndPhase, Recruit, SelectBattleClearing, SelectBattleTarget, SelectMoveDestination, SelectMoveSource
from ..enums import BuildingType, Faction, Phase, TokenType


@dataclass(frozen=True)
class SearchConfig:
    max_depth: int = 1
    branch_factor: int = 12


def choose_action(engine: Any, config: SearchConfig) -> Any:
    state = engine.get_state()
    if state.turn.current_faction != Faction.MARQUISE:
        raise ValueError("choose_action called outside Marquise turn")

    valid_actions = engine.get_valid_actions()
    if len(valid_actions) == 1:
        return valid_actions[0]

    best_score = float("-inf")
    best_action = valid_actions[0]
    for action in valid_actions[: config.branch_factor]:
        sim = engine.clone()
        sim._marquise_ai_enabled = False
        sim.apply_action(action)
        score = _evaluate_position(sim.get_state()) + _action_bias(action)
        if score > best_score:
            best_score = score
            best_action = action
    return best_action


def _evaluate_position(state: Any) -> float:
    marquise = state.marquise
    score = float(state.scores[Faction.MARQUISE] * 100)
    buildings = recruiters = sawmills = workshops = sympathy_penalty = cat_warriors = wood_tokens = 0

    for cid, warriors in state.board.warriors.items():
        cat_warriors += warriors.get(Faction.MARQUISE, 0)
        wood_tokens += state.board.tokens[cid].get(Faction.MARQUISE, []).count(TokenType.WOOD)
        sympathy_penalty += state.board.tokens[cid].get(Faction.ALLIANCE, []).count(TokenType.SYMPATHY)
        for building in state.board.buildings[cid].get(Faction.MARQUISE, []):
            buildings += 1
            recruiters += building == BuildingType.RECRUITER
            sawmills += building == BuildingType.SAWMILL
            workshops += building == BuildingType.WORKSHOP

    score += buildings * 22 + recruiters * 8 + sawmills * 10 + workshops * 6
    score += wood_tokens * 7 + cat_warriors * 3 - sympathy_penalty * 12
    score += marquise.warriors_in_supply * 0.3 + len(marquise.hand) * 0.4
    if state.turn.phase != Phase.EVENING:
        score -= 2
    return score


def _action_bias(action: Any) -> float:
    if isinstance(action, Build): return 25
    if isinstance(action, Recruit): return 15
    if isinstance(action, Craft): return 12
    if isinstance(action, SelectBattleClearing): return 11
    if isinstance(action, SelectBattleTarget): return 10
    if isinstance(action, SelectMoveSource): return 8
    if isinstance(action, SelectMoveDestination): return 7
    if isinstance(action, EndPhase): return -20
    return 0
