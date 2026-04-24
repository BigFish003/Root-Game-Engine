"""Shared clearing rulership calculations."""

from __future__ import annotations

from ..enums import Faction
from ..models import GameState


def clearing_rule_power(state: GameState, clearing_id: int, faction: Faction) -> int:
    """Combined warriors + buildings used for ruling checks."""

    return state.board.warriors[clearing_id][faction] + len(state.board.buildings[clearing_id][faction])


def rules_clearing(state: GameState, clearing_id: int, faction: Faction) -> bool:
    """Return whether faction rules clearing under faction-specific tie logic."""

    relevant = [Faction.MARQUISE, Faction.EYRIE, Faction.ALLIANCE]
    powers = {f: clearing_rule_power(state, clearing_id, f) for f in relevant}
    top = max(powers.values())
    if top == 0:
        return False
    if faction == Faction.EYRIE:
        return powers[faction] == top
    return powers[faction] > max(p for f, p in powers.items() if f != faction)


def ruler_of_clearing(state: GameState, clearing_id: int) -> Faction | None:
    """Return faction that rules the clearing, or None."""

    for faction in [Faction.MARQUISE, Faction.EYRIE, Faction.ALLIANCE]:
        if rules_clearing(state, clearing_id, faction):
            return faction
    return None
