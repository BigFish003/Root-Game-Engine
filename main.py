from __future__ import annotations
import math
import random
import copy
from root_engine.engine import RootEngine
from root_engine.enums import Faction
from typing import Dict, Optional, Any

c = 1.0


class Node:
    def __init__(self, parent: Optional["Node"], state: Any, faction: Faction):
        self.faction = faction
        self.state = state

        self.parent = parent
        self.children: Dict[Any, "Node"] = {}

        self.T = 0.0  # mean reward
        self.N = 0  # visit count

    def add_child(self, action: Any) -> None:
        child_state = copy.deepcopy(self.state)
        child_state.apply_action(action)
        self.children[action] = Node(self, child_state, self.faction)

    def choose_random_action(self, rollout_state: Any):
        return random.choice(rollout_state.get_valid_actions())

    def get_ucb_score(self) -> float:
        if self.N == 0:
            return float("inf")

        parent = self.parent
        if parent is None:
            return self.T

        if parent.N == 0:
            return float("inf")

        return self.T + c * math.sqrt(math.log(parent.N) / self.N)

    def is_leaf_node(self) -> bool:
        return len(self.children) == 0

    def rollout(self) -> float:
        rollout_state = copy.deepcopy(self.state)
        while rollout_state.get_state().turn.current_faction == self.faction:
            rollout_state.apply_action(self.choose_random_action(rollout_state))

        return rollout_state.get_state().scores[self.faction]

    def backpropagate(self, score: float) -> None:
        node: Optional[Node] = self
        while node is not None:
            node.T = ((node.T * node.N) + score) / (node.N + 1)
            node.N += 1
            node = node.parent


base = engine = RootEngine(seed=7, excluded_factions={Faction.VAGABOND}, marquise_ai_enabled=True,eyrie_ai_enabled=True)
for i in range(5000):
    pass