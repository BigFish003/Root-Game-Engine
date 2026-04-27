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

actions = [0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,1,1,-1,0,0,0,2,0,0,5,0,0,0,0,0]
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

def exec_marq_minmax():

    start_state = engine.get_observation(Faction.ALLIANCE)
    start_faction = start_state.current_faction


    end_states = []

    def search(current_engine, depth=0, max_depth=50):
        state = current_engine.get_observation(Faction.ALLIANCE)
        current_player = state.current_faction
        actions = current_engine.get_valid_actions()

        # Stop if the turn moved to another faction/player
        if current_player != start_faction:
            end_states.append(state)
            return

        # Safety stop so recursion does not run forever
        if depth >= max_depth:
            end_states.append(state)
            return

        # If there are no more actions, this is an end state
        if not actions:
            end_states.append(state)
            return

        # Try every valid action from this state
        for action in actions:
            next_engine = current_engine.clone()
            next_engine.apply_action(action)
            search(next_engine, depth + 1, max_depth)

    search(engine)

    print(f"Found {len(end_states)} possible end states")

    # Render the first end state just to check it worked
    if end_states:
        render.render_board(end_states[0], "game_state.png")
    else:
        render.render_board(start_state, "game_state.png")

    return end_states


exec_marq_minmax()


