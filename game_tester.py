from root_engine.engine import RootEngine
from root_engine.enums import Faction
from state_renderer import render
from state_renderer.render import state_renderer
import keyboard

engine = RootEngine(seed=7)
render = state_renderer()

marquise_observation = engine.get_observation(Faction.MARQUISE)
render.render_board(marquise_observation, 'game_state.png')
print(engine.get_valid_actions())

actions = [0,1,1,1,1,0,0,1,1,0,0]

for i in range(len(actions)):
    engine.apply_action(engine.get_valid_actions()[actions[i]])
    marquise_observation = engine.get_observation(Faction.MARQUISE)
    render.render_board(marquise_observation, 'game_state.png')
    print("Current Faction: ", engine.get_state().turn.current_faction, "Current Phase: ", engine.get_state().turn.phase)
    print(engine.get_valid_actions())
