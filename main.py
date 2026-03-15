from root_engine.engine import RootEngine
from root_engine.enums import Faction
from root_engine.renderer import RootRenderer
from root_engine.render import TextRenderer, VisualRenderer

engine = RootEngine(seed=7)
renderer = RootRenderer()
text_renderer = TextRenderer()
visual_renderer = VisualRenderer()

marquise_observation = engine.get_observation(Faction.MARQUISE)
visual_renderer.render_to_file(marquise_observation, "root_marquise_observation1.svg")

actions = engine.get_valid_actions()
engine.apply_action(actions[1])

marquise_observation = engine.get_observation(Faction.MARQUISE)
visual_renderer.render_to_file(marquise_observation, "root_marquise_observation2.svg")