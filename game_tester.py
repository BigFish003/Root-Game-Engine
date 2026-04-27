from __future__ import annotations

import json

from root_engine.engine import RootEngine
from root_engine.enums import Faction
from state_renderer.render import state_renderer

engine = RootEngine(seed=7, excluded_factions={Faction.VAGABOND})
render = state_renderer()

marquise_observation = engine.get_observation(Faction.MARQUISE)
render.render_board(marquise_observation, "game_state.png")
print(engine.get_valid_actions())

actions = [0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, -1, 0, 0, 0, 2, 0, 0, 5, 0, 0, 0, 0, 0]
r = True

for i in range(len(actions)):
    valid_actions = engine.get_valid_actions()
    print(len(valid_actions))
    engine.apply_action(valid_actions[actions[i]])
    if r:
        obs = engine.get_observation(Faction.ALLIANCE)
        render.render_board(obs, "game_state.png")
    print("Current Faction: ", engine.get_state().turn.current_faction, "Current Phase: ", engine.get_state().turn.phase)
    if i == 30:
        engine._state.alliance.supporters.append(1)
        engine._state.alliance.supporters.append(1)
    print(engine.get_valid_actions())


def _state_key(current_engine: RootEngine) -> str:
    """Create a canonical, hashable representation of full engine state."""

    return json.dumps(current_engine.to_dict(), sort_keys=True)


def exec_alliance_end_state_search(current_engine: RootEngine) -> list:
    """Find all unique reachable end states for the current Alliance turn."""

    start_state = current_engine.get_observation(Faction.ALLIANCE)
    start_faction = start_state.current_faction

    if start_faction != Faction.ALLIANCE:
        raise ValueError("Search must start on the Alliance turn")

    end_states = []
    seen_non_terminal = set()
    seen_terminal = set()

    def search(engine_node: RootEngine) -> None:
        state = engine_node.get_observation(Faction.ALLIANCE)

        if state.current_faction != start_faction:
            terminal_key = _state_key(engine_node)
            if terminal_key not in seen_terminal:
                seen_terminal.add(terminal_key)
                end_states.append(state)
            return

        node_key = _state_key(engine_node)
        if node_key in seen_non_terminal:
            return
        seen_non_terminal.add(node_key)

        actions = engine_node.get_valid_actions()
        if not actions:
            terminal_key = _state_key(engine_node)
            if terminal_key not in seen_terminal:
                seen_terminal.add(terminal_key)
                end_states.append(state)
            return

        for action in actions:
            next_engine = engine_node.clone()
            next_engine.apply_action(action)
            search(next_engine)

    search(current_engine.clone())

    print(f"Found {len(end_states)} unique Alliance turn end states")

    if end_states:
        render.render_board(end_states[0], "game_state.png")
    else:
        render.render_board(start_state, "game_state.png")

    return end_states


exec_alliance_end_state_search(engine)
