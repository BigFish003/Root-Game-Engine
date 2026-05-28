"""Public engine API."""

from __future__ import annotations

from typing import Optional

from .action_generation import get_valid_actions
from .actions import (
    AddToDecree,
    Build,
    Craft,
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
from .enums import Faction
from .models import GameState
from .observation import Observation, build_observation
from .ai.eyrie_ai import SearchConfig as EyrieSearchConfig, choose_action as choose_eyrie_action
from .ai.marquise_ai import SearchConfig as MarquiseSearchConfig, choose_action as choose_marquise_action
from .rules import alliance, base_rules, eyrie, marquise
from .rules.scoring import WINNING_SCORE
from .state import clone_state, create_initial_state
from .utils.debug import format_state
from .utils.serialize import to_jsonable


class RootEngine:
    """Root base-game engine focused on state transitions and legal actions."""

    def __init__(
        self,
        seed: Optional[int] = None,
        excluded_factions: Optional[set[Faction]] = None,
        marquise_ai_enabled: bool = False,
        marquise_ai_max_depth: int = 3,
        marquise_ai_branch_factor: int = 5,
        eyrie_ai_enabled: bool = False,
        eyrie_ai_max_depth: int = 2,
        eyrie_ai_branch_factor: int = 8,
    ) -> None:
        self._excluded_factions = set(excluded_factions or set())
        self._marquise_ai_enabled = marquise_ai_enabled
        self._marquise_ai_config = MarquiseSearchConfig(
            max_depth=marquise_ai_max_depth,
            branch_factor=marquise_ai_branch_factor,
        )
        self._eyrie_ai_enabled = eyrie_ai_enabled
        self._eyrie_ai_config = EyrieSearchConfig(
            max_depth=eyrie_ai_max_depth,
            branch_factor=eyrie_ai_branch_factor,
        )
        self._state = create_initial_state(seed, excluded_factions=self._excluded_factions)
        self._auto_play_ai_turns_if_enabled()

    def reset(self, seed: int | None = None) -> GameState:
        self._state = create_initial_state(seed, excluded_factions=self._excluded_factions)
        self._auto_play_ai_turns_if_enabled()
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
        if isinstance(action, EndPhase):
            base_rules.advance_phase(self._state)
            self._auto_play_ai_turns_if_enabled()
            return

        if faction == Faction.MARQUISE:
            self._apply_marquise_action(action)
        elif faction == Faction.EYRIE:
            self._apply_eyrie_action(action)
        elif faction == Faction.ALLIANCE:
            self._apply_alliance_action(action)
        else:
            raise ValueError("Current faction action handlers are not implemented yet")

        self._auto_play_ai_turns_if_enabled()

    def clone(self) -> "RootEngine":
        clone = RootEngine(
            seed=self._state.seed,
            excluded_factions=set(self._excluded_factions),
            marquise_ai_enabled=False,
            marquise_ai_max_depth=self._marquise_ai_config.max_depth,
            marquise_ai_branch_factor=self._marquise_ai_config.branch_factor,
            eyrie_ai_enabled=False,
            eyrie_ai_max_depth=self._eyrie_ai_config.max_depth,
            eyrie_ai_branch_factor=self._eyrie_ai_config.branch_factor,
        )
        clone._state = clone_state(self._state)
        clone._marquise_ai_enabled = self._marquise_ai_enabled
        clone._eyrie_ai_enabled = self._eyrie_ai_enabled
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


    def set_marquise_ai_enabled(self, enabled: bool) -> None:
        self._marquise_ai_enabled = enabled
        self._auto_play_ai_turns_if_enabled()

    def set_eyrie_ai_enabled(self, enabled: bool) -> None:
        self._eyrie_ai_enabled = enabled
        self._auto_play_ai_turns_if_enabled()

    def _auto_play_ai_turns_if_enabled(self) -> None:
        if not self._marquise_ai_enabled and not self._eyrie_ai_enabled:
            return

        steps = 0
        while not self.is_terminal():
            current = self._state.turn.current_faction
            if current == Faction.MARQUISE and not self._marquise_ai_enabled:
                return
            if current == Faction.EYRIE and not self._eyrie_ai_enabled:
                return
            if current not in (Faction.MARQUISE, Faction.EYRIE):
                return
            steps += 1
            if steps > 200:
                return
            valid_actions = self.get_valid_actions()
            if not valid_actions:
                return
            if current == Faction.MARQUISE:
                chosen_action = choose_marquise_action(self, self._marquise_ai_config)
            else:
                chosen_action = choose_eyrie_action(self, self._eyrie_ai_config)
            if not any(a == chosen_action for a in valid_actions):
                chosen_action = valid_actions[0]

            if isinstance(chosen_action, EndPhase):
                base_rules.advance_phase(self._state)
            else:
                if current == Faction.MARQUISE:
                    self._apply_marquise_action(chosen_action)
                else:
                    self._apply_eyrie_action(chosen_action)

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
