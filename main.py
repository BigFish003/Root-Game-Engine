from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from root_engine.engine import RootEngine
from root_engine.enums import Faction
from typing import Any, List, Dict, Union, Optional

c = 1.0

class Node:
    def __init__(self, parent: Optional[Node], state, faction: Faction):

        self.faction = faction
        self.state = state

        self.parent = parent
        self.children = []

        self.is_expanded = False
        self.has_outcome = False

        self.T = 0 #total reward
        self.N = 0 #visit count

    def add_child(self, action):
        self.children[action] = Node(self, self.state, self.faction)
        self.children[action].apply_action(action)

    def choose_random_action(self):
        return random.choice(self.state.get_valid_actions())

    def getUCBscore(self):

        if self.N == 0:
            return float('inf')

        top_node = self
        if top_node.parent:
            top_node = top_node.parent

        return (self.T / self.N) + c * math.sqrt(math.log(top_node.N) / self.N)

    def is_leaf_node(self):
        if len(self.children) > 0:
            return False
        return True

    def rollout(self):
        while self.state.get_state().turn.current_faction == self.faction:
            self.state.apply_action(self.choose_random_action())
        score = self.state.get_state().scores[self.faction]
        self.T = ((self.T * self.N) + score )/(self.N+1)
        self.N += 1

ground_state = RootEngine(seed=7)
node = Node(None, ground_state, ground_state.get_state().turn.current_faction)
while True:
    if node.is_leaf_node():
        if node.N == 0:
            node.rollout()
        else:
            actions = node.state.get_valid_actions()
            for action in actions:
                node.add_child(action)
            node = node.children[random.choice(actions)]
    else:
        scores = []
        for child in node.children:
            scores.append(child.getUCBscore())
        node = node.children[scores.index(max(scores))]

