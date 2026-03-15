"""Debug formatting helpers."""

from __future__ import annotations

from ..enums import Faction
from ..models import GameState


def format_state(state: GameState) -> str:
    """Pretty-print a concise game snapshot."""

    lines = [
        f"Round {state.turn.round_number} | {state.turn.current_faction.value} | {state.turn.phase.value}",
        f"Decision: {state.decision_context.decision_type.value}",
        "Scores: " + ", ".join(f"{f.value}={state.scores[f]}" for f in Faction),
        "Clearings:",
    ]
    for cid in sorted(state.board.clearings):
        w = state.board.warriors[cid]
        b = state.board.buildings[cid]
        t = state.board.tokens[cid]
        lines.append(
            f"  C{cid}: W({{m:{w[Faction.MARQUISE]}, e:{w[Faction.EYRIE]}, a:{w[Faction.ALLIANCE]}}}) "
            f"B(m={len(b[Faction.MARQUISE])}, e={len(b[Faction.EYRIE])}) "
            f"T(m={len(t[Faction.MARQUISE])}, a={len(t[Faction.ALLIANCE])})"
        )
    return "\n".join(lines)
