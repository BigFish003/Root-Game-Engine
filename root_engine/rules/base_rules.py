"""Cross-faction phase and turn progression rules."""

from __future__ import annotations

from ..enums import DecisionType, Phase
from ..models import GameState


def advance_phase(state: GameState) -> None:
    """Move from birdsong->daylight->evening->next faction."""

    if state.turn.phase == Phase.BIRDSONG:
        state.turn.phase = Phase.DAYLIGHT
    elif state.turn.phase == Phase.DAYLIGHT:
        state.turn.phase = Phase.EVENING
    else:
        _advance_to_next_faction(state)
    state.decision_context = state.decision_context.__class__(decision_type=DecisionType.MAIN_ACTION)


def _advance_to_next_faction(state: GameState) -> None:
    order = state.turn.turn_order
    idx = order.index(state.turn.current_faction)
    nxt = (idx + 1) % len(order)
    if nxt == 0:
        state.turn.round_number += 1
    state.turn.current_faction = order[nxt]
    state.turn.phase = Phase.BIRDSONG
