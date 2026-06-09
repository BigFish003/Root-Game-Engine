from __future__ import annotations

import json

from root_engine.engine import RootEngine
from root_engine.enums import Faction
from state_renderer.render import state_renderer

engine = RootEngine(seed=7, marquise_ai_enabled=True,eyrie_ai_enabled=True)
render = state_renderer()

marquise_observation = engine.get_observation(Faction.MARQUISE)
render.render_board(marquise_observation, "game_state.png")
print(engine.get_valid_actions())
print(engine.get_state().alliance.supporters)

actions = [0]
r = True
for i in range(len(actions)):
    valid_actions = engine.get_valid_actions()
    engine.apply_action(valid_actions[actions[i]])
    if r:
        obs = engine.get_observation(Faction.ALLIANCE)
        render.render_board(obs, "game_state.png")
    print("Current Faction: ", engine.get_state().turn.current_faction, "Current Phase: ", engine.get_state().turn.phase)
    print(engine.get_valid_actions())

