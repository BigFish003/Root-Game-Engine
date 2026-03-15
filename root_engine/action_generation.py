"""Valid action generation dispatch."""

from __future__ import annotations

from .models import GameState
from .enums import Faction
from .rules import alliance, eyrie, marquise, vagabond


def get_valid_actions(state: GameState) -> list:
    """Return legal atomic actions for the current decision point."""

    faction = state.turn.current_faction
    if faction == Faction.MARQUISE:
        return marquise.valid_actions(state)
    if faction == Faction.EYRIE:
        return eyrie.valid_actions(state)
    if faction == Faction.ALLIANCE:
        return alliance.valid_actions(state)
    return vagabond.valid_actions(state)
