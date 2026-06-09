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
            lines.append(
                f"- {faction.value}: score={state.scores[faction]} "
                f"hand={list(board.hand)} "
                f"Crafted Cards={state.crafted_cards.get(faction, [])} "
                f"Crafted Items={_format_items(state.crafted_items.get(faction, {}))}"
            )
        lines.append(f"Item supply: {_format_items(state.item_supply)}")
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
            lines.append(f"  Crafted Cards: {board.crafted_cards}")
            lines.append(f"  Crafted Items: {_format_public_items(board.crafted_items)}")
        lines.extend(self._render_observer_private_lines(obs))
        return "\n".join(lines)

    def render_observer_private(self, obs: Observation) -> str:
        """Render private observation details for the requesting faction only."""

        return "\n".join(self._render_observer_private_lines(obs))

    def _render_observer_private_lines(self, obs: Observation) -> list[str]:
        board = obs.factions[obs.observer]
        lines = [
            "Observer private info:",
            f"- hand: {board.hand if board.hand is not None else []}",
        ]
        if "supporters" in board.private_data:
            lines.append(f"- supporters: {board.private_data['supporters']}")
        return lines


def _format_items(items: dict) -> str:
    if not items:
        return "-"
    return ", ".join(
        f"{getattr(item, 'value', item)}={count}"
        for item, count in sorted(items.items(), key=lambda entry: str(entry[0]))
    )


def _format_public_items(items: dict[str, int]) -> str:
    if not items:
        return "-"
    return ", ".join(f"{item}={count}" for item, count in sorted(items.items()))
