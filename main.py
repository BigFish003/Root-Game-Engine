from root_engine.engine import RootEngine
from root_engine.enums import Faction
from state_renderer.render import state_renderer


# Min Max Algorithm / End State Search

def exec_marq_minmax():
    engine = RootEngine(seed=7, excluded_factions={Faction.VAGABOND})
    render = state_renderer()

    start_state = engine.get_observation(Faction.MARQUISE)
    start_faction = start_state.current_faction


    end_states = []

    def search(current_engine, depth=0, max_depth=50):
        x = 0
        state = current_engine.get_observation(Faction.MARQUISE)
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
            x += 1
            print("cloned state, so far: ", str(x))
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