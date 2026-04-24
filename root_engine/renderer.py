"""Text renderer for game state and player observations."""

from __future__ import annotations

from .enums import Faction
from .models import GameState
from .observation import Observation


class RootRenderer:
    """Render full game state or filtered observation to plain text."""

    def render(self, payload: GameState | Observation) -> str:
        if isinstance(payload, Observation):
            return self._render_observation(payload)
        return self._render_state(payload)

    def _render_state(self, state: GameState) -> str:
        lines = [
            f"Turn: {state.turn.current_faction.value} / {state.turn.phase.value}",
            "Faction boards:",
        ]
        for faction in Faction:
            board = state.faction_state(faction)
            lines.append(f"- {faction.value}: score={state.scores[faction]} hand={list(board.hand)}")
        return "\n".join(lines)

    def _render_observation(self, obs: Observation) -> str:
        lines = [
            f"Observer: {obs.observer.value}",
            f"Turn: {obs.current_faction.value} / {obs.current_phase}",
            "Faction boards:",
        ]
        for faction in Faction:
            board = obs.factions[faction]
            hand_view = (
                str(board.hand)
                if board.hand is not None
                else f"hidden(count={board.hand_count})"
            )
            lines.append(f"- {faction.value}: score={board.score} hand={hand_view}")
        return "\n".join(lines)
