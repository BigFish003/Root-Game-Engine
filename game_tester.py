from root_engine.engine import RootEngine
from root_engine.actions import EndPhase, SpreadSympathy
from root_engine.enums import Faction
from state_renderer import render
from state_renderer.render import state_renderer
import keyboard

engine = RootEngine(seed=7)
render = state_renderer()

marquise_observation = engine.get_observation(Faction.MARQUISE)
render.render_board(marquise_observation, 'game_state.png')
print(engine.get_valid_actions())

actions = [0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0]

for i in range(len(actions)):
    valid_actions = engine.get_valid_actions()
    action_index = actions[i]
    # NOTE:
    # Index-based action selection is fragile because legal action lists change
    # after each move. A fixed index may select EndPhase unexpectedly.
    if action_index >= len(valid_actions):
        action_index = len(valid_actions) - 1
    engine.apply_action(valid_actions[action_index])
    marquise_observation = engine.get_observation(Faction.MARQUISE)
    render.render_board(marquise_observation, 'game_state.png')
    print("Current Faction: ", engine.get_state().turn.current_faction, "Current Phase: ", engine.get_state().turn.phase)
    print(list(enumerate(engine.get_valid_actions())))


# Example: if you want to verify repeated Alliance sympathy in birdsong,
# choose actions by type rather than index.
while engine.get_state().turn.current_faction != Faction.ALLIANCE:
    engine.apply_action(EndPhase())
while engine.get_state().turn.phase.value == "birdsong":
    spreads = [a for a in engine.get_valid_actions() if isinstance(a, SpreadSympathy)]
    if not spreads:
        break
    engine.apply_action(spreads[0])
    print("Spread sympathy, remaining actions:", engine.get_valid_actions())
