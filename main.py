from root_engine.engine import RootEngine
from root_engine.enums import Faction
from root_engine.render import TextRenderer, VisualRenderer

engine = RootEngine(seed=7)
text_renderer = TextRenderer()
visual_renderer = VisualRenderer()

print("=== FULL STATE (TEXT) ===")
print(text_renderer.render(engine.get_state()))

visual_renderer.render_to_file(engine.get_state(), "root_full_state.svg")

print("\n=== MARQUISE OBSERVATION (TEXT) ===")
marquise_observation = engine.get_observation(Faction.MARQUISE)
print(text_renderer.render(marquise_observation))

visual_renderer.render_to_file(marquise_observation, "root_marquise_observation.svg")
print("\nWrote SVGs: root_full_state.svg, root_marquise_observation.svg")
