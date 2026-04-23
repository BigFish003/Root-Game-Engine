from root_engine.engine import RootEngine
from root_engine.enums import Faction

engine = RootEngine(seed=7)

marquise_observation = engine.get_observation(Faction.MARQUISE)




