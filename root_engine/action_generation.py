"""Valid action generation dispatch."""

from __future__ import annotations

from .models import GameState
from .enums import Faction
from .actions import EndPhase
from .rules import alliance, eyrie, marquise, vagabond


def get_valid_actions(state: GameState) -> list:
    """Return legal atomic actions for the current decision point."""

    faction = state.turn.current_faction
    if faction == Faction.MARQUISE:
        actions = marquise.valid_actions(state)
    elif faction == Faction.EYRIE:
        actions = eyrie.valid_actions(state)
    elif faction == Faction.ALLIANCE:
        actions = alliance.valid_actions(state)
    else:
        actions = vagabond.valid_actions(state)
    return _prioritize_end_phase(actions)


def _prioritize_end_phase(actions: list) -> list:
    """Move EndPhase to the front whenever it is an available action."""

    end_phase_actions = [action for action in actions if isinstance(action, EndPhase)]
    if not end_phase_actions:
        return actions
    non_end_phase_actions = [action for action in actions if not isinstance(action, EndPhase)]
    return end_phase_actions + non_end_phase_actions
