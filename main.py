from root_engine.engine import RootEngine
from root_engine.enums import Faction

engine = RootEngine(seed=7)

marquise_observation = engine.get_observation(Faction.MARQUISE)

action_indices = []
print(marquise_observation)


for i in range(len(action_indices)):
    valid_actions = engine.get_valid_actions()
    print(valid_actions)
    engine.apply_action(valid_actions[action_indices[i]])

    marquise_observation = engine.get_observation(Faction.MARQUISE)

valid_actions = engine.get_valid_actions()
print(valid_actions)



