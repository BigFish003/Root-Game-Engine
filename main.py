from root_engine.engine import RootEngine
from root_engine.enums import Faction
from root_engine.renderer import RootRenderer
from root_engine.render import TextRenderer, VisualRenderer

engine = RootEngine(seed=7)
renderer = RootRenderer()
text_renderer = TextRenderer()
visual_renderer = VisualRenderer()

marquise_observation = engine.get_observation(Faction.MARQUISE)
visual_renderer.render_to_file(marquise_observation, "observations/root_marquise_observation0.svg")

action_indices = [2,2,2,2,2,2,2,2,2]



for i in range(len(action_indices)):
    valid_actions = engine.get_valid_actions()
    print(valid_actions)
    engine.apply_action(valid_actions[action_indices[i]])

    marquise_observation = engine.get_observation(Faction.MARQUISE)
    visual_renderer.render_to_file(marquise_observation, f"observations/root_marquise_observation{i+1}.svg")

valid_actions = engine.get_valid_actions()
print(valid_actions)



