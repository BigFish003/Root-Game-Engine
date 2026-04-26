"""Public engine API."""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from .action_generation import get_valid_actions
from .actions import (
    AddToDecree,
    Build,
    Craft,
    EndDecision,
    EndPhase,
    FallIntoTurmoil,
    Mobilize,
    Organize,
    Recruit,
    Revolt,
    SelectEyrieLeader,
    SelectBattleClearing,
    SelectBattleTarget,
    SelectMoveDestination,
    SelectMoveSource,
    SpreadSympathy,
    Train,
)
from .enums import DecisionType, Faction
from .models import GameState
from .observation import Observation, build_observation
from .rules import alliance, base_rules, eyrie, marquise
from .rules.scoring import WINNING_SCORE
from .state import clone_state, create_initial_state
from .utils.debug import format_state
from .utils.serialize import to_jsonable


class RootEngine:
    """Root base-game engine focused on state transitions and legal actions."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self._state = create_initial_state(seed)

    def reset(self, seed: int | None = None) -> GameState:
        self._state = create_initial_state(seed)
        return self._state

    def get_state(self) -> GameState:
        return self._state

    def get_valid_actions(self) -> list:
        return get_valid_actions(self._state)

    def get_observation(self, faction: Faction) -> Observation:
        return build_observation(self._state, faction)

    def apply_action(self, action) -> None:
        if not any(a == action for a in self.get_valid_actions()):
            raise ValueError(f"Illegal action for current context: {action}")
        faction = self._state.turn.current_faction
        if isinstance(action, EndDecision):
            self._state.decision_context = replace(
                self._state.decision_context,
                decision_type=DecisionType.MAIN_ACTION,
                selected_source=None,
                selected_destination=None,
                selected_battle_clearing=None,
            )
            return
        if isinstance(action, EndPhase):
            base_rules.advance_phase(self._state)
            return

        if faction == Faction.MARQUISE:
            self._apply_marquise_action(action)
        elif faction == Faction.EYRIE:
            self._apply_eyrie_action(action)
        elif faction == Faction.ALLIANCE:
            self._apply_alliance_action(action)
        else:
            raise ValueError("Current faction action handlers are not implemented yet")

    def clone(self) -> "RootEngine":
        clone = RootEngine(seed=self._state.seed)
        clone._state = clone_state(self._state)
        return clone

    def is_terminal(self) -> bool:
        return any(score >= WINNING_SCORE for score in self._state.scores.values())

    def get_winner(self) -> Faction | None:
        if not self.is_terminal():
            return None
        return max(self._state.scores, key=self._state.scores.get)

    def to_dict(self) -> dict:
        return to_jsonable(self._state)

    def pretty_print(self) -> str:
        return format_state(self._state)

    def _apply_marquise_action(self, action) -> None:
        if isinstance(action, Recruit):
            marquise.apply_recruit(self._state, action)
        elif isinstance(action, Build):
            marquise.apply_build(self._state, action)
        elif isinstance(action, SelectMoveSource):
            marquise.apply_move_source(self._state, action)
        elif isinstance(action, SelectMoveDestination):
            marquise.apply_move_destination(self._state, action)
        elif isinstance(action, SelectBattleClearing):
            marquise.apply_battle_select_clearing(self._state, action)
        elif isinstance(action, SelectBattleTarget):
            marquise.apply_battle_select_target(self._state, action)
        elif isinstance(action, Craft):
            marquise.apply_craft(self._state, action)

    def _apply_eyrie_action(self, action) -> None:
        if isinstance(action, Recruit):
            eyrie.apply_recruit(self._state, action)
        elif isinstance(action, Build):
            eyrie.apply_build(self._state, action)
        elif isinstance(action, SelectMoveSource):
            eyrie.apply_move_source(self._state, action)
        elif isinstance(action, SelectMoveDestination):
            eyrie.apply_move_destination(self._state, action)
        elif isinstance(action, SelectBattleClearing):
            eyrie.apply_battle_select_clearing(self._state, action)
        elif isinstance(action, SelectBattleTarget):
            eyrie.apply_battle_select_target(self._state, action)
        elif isinstance(action, Craft):
            eyrie.apply_craft(self._state, action)
        elif isinstance(action, AddToDecree):
            eyrie.apply_add_to_decree(self._state, action)
        elif isinstance(action, FallIntoTurmoil):
            eyrie.apply_fall_into_turmoil(self._state, action)
        elif isinstance(action, SelectEyrieLeader):
            eyrie.apply_select_leader(self._state, action)

    def _apply_alliance_action(self, action) -> None:
        if isinstance(action, Revolt):
            alliance.apply_revolt(self._state, action)
        elif isinstance(action, SpreadSympathy):
            alliance.apply_spread_sympathy(self._state, action)
        elif isinstance(action, Craft):
            alliance.apply_craft(self._state, action)
        elif isinstance(action, Mobilize):
            alliance.apply_mobilize(self._state, action)
        elif isinstance(action, Train):
            alliance.apply_train(self._state, action)
        elif isinstance(action, SelectMoveSource):
            alliance.apply_move_source(self._state, action)
        elif isinstance(action, SelectMoveDestination):
            alliance.apply_move_destination(self._state, action)
        elif isinstance(action, SelectBattleClearing):
            alliance.apply_battle_select_clearing(self._state, action)
        elif isinstance(action, SelectBattleTarget):
            alliance.apply_battle_select_target(self._state, action)
        elif isinstance(action, Recruit):
            alliance.apply_recruit(self._state, action)
        elif isinstance(action, Organize):
            alliance.apply_organize(self._state, action)
