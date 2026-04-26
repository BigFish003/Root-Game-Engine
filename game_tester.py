from root_engine.engine import RootEngine
from root_engine.actions import EndPhase, SpreadSympathy
from root_engine.enums import Faction
from state_renderer.render import state_renderer
import keyboard

engine = RootEngine(seed=7,excluded_factions={Faction.VAGABOND})
render = state_renderer()

marquise_observation = engine.get_observation(Faction.MARQUISE)
render.render_board(marquise_observation, 'game_state.png')
print(engine.get_valid_actions())

actions = [0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,1,1,-1,0,0,0,2,0,0,5,0,0,0,0,0,1,1,0,1,0,2]
r = True

for i in range(len(actions)):
    valid_actions = engine.get_valid_actions()
    print(len(valid_actions))
    engine.apply_action(valid_actions[actions[i]])
    if r:
        obs = engine.get_observation(Faction.ALLIANCE)
        render.render_board(obs, 'game_state.png')
    print("Current Faction: ", engine.get_state().turn.current_faction, "Current Phase: ", engine.get_state().turn.phase)
    if i== 30:
        engine._state.alliance.supporters.append(1)
        engine._state.alliance.supporters.append(1)
    print(engine.get_valid_actions())
