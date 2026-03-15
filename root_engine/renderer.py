"""Rendering helpers that consume only passed state/observation data."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import Faction
from .models import GameState
from .observation import Observation


@dataclass
class RootRenderer:
    """Text renderer for full game states or faction observations."""

    include_legal_actions: bool = False

    def render(self, view: GameState | Observation) -> str:
        if isinstance(view, GameState):
            return self._render_full_state(view)
        return self._render_observation(view)

    def _render_full_state(self, state: GameState) -> str:
        lines = [
            f"Round {state.turn.round_number} | {state.turn.current_faction.value} | {state.turn.phase.value}",
            f"Decision: {state.decision_context.decision_type.value}",
            "Scores: " + ", ".join(f"{f.value}={state.scores[f]}" for f in Faction),
            "Board:",
        ]
        for cid in sorted(state.board.clearings):
            clearing = state.board.clearings[cid]
            lines.append(
                f"  C{cid} ({clearing.suit.value}) adj={sorted(clearing.adjacent_clearings)} "
                f"ruler={self._render_ruler_from_state(state, cid)}"
            )
            lines.append(
                "    warriors="
                + ", ".join(f"{f.value}:{state.board.warriors[cid][f]}" for f in Faction)
            )
            lines.append(
                "    buildings="
                + ", ".join(
                    f"{f.value}:{[b.value for b in state.board.buildings[cid][f]]}" for f in Faction
                )
            )
            lines.append(
                "    tokens="
                + ", ".join(
                    f"{f.value}:{[t.value for t in state.board.tokens[cid][f]]}" for f in Faction
                )
            )

        lines.append("Faction boards:")
        for faction in Faction:
            fs = state.faction_state(faction)
            lines.append(
                f"  {faction.value}: score={state.scores[faction]} hand={list(fs.hand)} "
                f"crafted={list(fs.crafted_effects)}"
            )
        lines.append(f"Discard pile: {list(state.discard_pile)}")
        return "\n".join(lines)

    def _render_observation(self, obs: Observation) -> str:
        lines = [
            f"Round {obs.round_number} | {obs.current_faction.value} | {obs.current_phase}",
            f"Observer: {obs.observer.value}",
            f"Decision: {obs.decision['decision_type']}",
            "Scores: " + ", ".join(f"{f.value}={obs.scores[f]}" for f in Faction),
            "Board:",
        ]
        for cid in sorted(obs.clearings):
            clearing = obs.clearings[cid]
            lines.append(
                f"  C{cid} ({clearing.suit.value}) adj={sorted(clearing.adjacent_clearings)} "
                f"ruler={clearing.ruler.value if clearing.ruler else 'none'}"
            )
            lines.append(
                "    warriors=" + ", ".join(f"{f.value}:{clearing.warriors[f]}" for f in Faction)
            )
            lines.append(
                "    buildings=" + ", ".join(f"{f.value}:{clearing.buildings[f]}" for f in Faction)
            )
            lines.append("    tokens=" + ", ".join(f"{f.value}:{clearing.tokens[f]}" for f in Faction))

        lines.append("Faction boards:")
        for faction in Faction:
            fb = obs.factions[faction]
            hand_display = fb.hand if fb.hand is not None else f"hidden(count={fb.hand_count})"
            lines.append(
                f"  {faction.value}: score={fb.score} hand={hand_display} crafted={fb.crafted_effects}"
            )
            if fb.public_data:
                lines.append(f"    public={fb.public_data}")
            if fb.private_data:
                lines.append(f"    private={fb.private_data}")
        lines.append(f"Discard pile: {obs.discard_pile}")
        return "\n".join(lines)

    def _render_ruler_from_state(self, state: GameState, clearing_id: int) -> str:
        rule_counts = {
            faction: state.board.warriors[clearing_id][faction] + len(state.board.buildings[clearing_id][faction])
            for faction in [Faction.MARQUISE, Faction.EYRIE, Faction.ALLIANCE]
        }
        top = max(rule_counts.values())
        if top == 0:
            return "none"
        leaders = [f for f, count in rule_counts.items() if count == top]
        return leaders[0].value if len(leaders) == 1 else "none"
