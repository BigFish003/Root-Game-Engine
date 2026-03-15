# Root-Game-Engine

## Observation + rendering example

```python
from root_engine.engine import RootEngine
from root_engine.enums import Faction
from root_engine.renderer import RootRenderer

engine = RootEngine(seed=7)
renderer = RootRenderer()

# Full debug rendering (all hidden info visible)
print(renderer.render(engine.get_state()))

# Player-specific rendering (hidden info masked)
marquise_observation = engine.get_observation(Faction.MARQUISE)
print(renderer.render(marquise_observation))
```
