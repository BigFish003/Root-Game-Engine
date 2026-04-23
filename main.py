from root_engine.engine import RootEngine
from root_engine.enums import Faction
from state_renderer import render
from state_renderer.render import state_renderer

engine = RootEngine(seed=7)
render = state_renderer()

marquise_observation = engine.get_observation(Faction.MARQUISE)
print(marquise_observation)
render.render_board(marquise_observation, 'game_state.png')




