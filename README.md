# Root-Game-Engine

## Observation + rendering example

```python
from root_engine.engine import RootEngine
from root_engine.enums import Faction
from root_engine.render import TextRenderer, VisualRenderer

engine = RootEngine(seed=7)
text_renderer = TextRenderer()
visual_renderer = VisualRenderer()

# Full debug rendering (all hidden info visible)
print(text_renderer.render(engine.get_state()))

# Full-state visual rendering (debug SVG)
visual_renderer.render_to_file(engine.get_state(), "root_full_state.svg")

# Player-specific visual rendering (hidden info masked)
marquise_observation = engine.get_observation(Faction.MARQUISE)
visual_renderer.render_to_file(marquise_observation, "root_marquise_view.svg")
```

The engine stays fully headless and independent from rendering. Rendering modules consume only the state/observation objects passed to them.
