from __future__ import annotations
import math
import random
import copy
from dataclasses import dataclass
from typing import Dict, Optional, Any

import torch

from NN.allianceNN import AllianceNN
from root_engine.actions import (
    Build,
    Craft,
    EndDecision,
    EndPhase,
    Mobilize,
    Organize,
    Recruit,
    ResolveMove,
    Revolt,
    SelectBattleClearing,
    SelectBattleTarget,
    SelectMoveDestination,
    SelectMoveSource,
    SpreadSympathy,
    Train,
)
from root_engine.engine import RootEngine
from root_engine.enums import BuildingType, Faction

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


@dataclass(frozen=True)
class ActionIndex:
    actions: list[Any]
    lookup: dict[Any, int]


def build_alliance_action_index() -> ActionIndex:
    clearings = range(1, 13)
    factions = (Faction.MARQUISE, Faction.EYRIE, Faction.VAGABOND)
    building_types = BuildingType.BASE
    card_ids = range(54)

    actions: list[Any] = [EndPhase(), EndDecision()]

    for cid in clearings:
        actions.extend(
            [
                Recruit(cid),
                Revolt(cid),
                SpreadSympathy(cid),
                Organize(cid),
                SelectMoveSource(cid),
                SelectBattleClearing(cid),
            ]
        )
        actions.append(Build(cid, building_types))
        for warriors in range(1, 11):
            actions.append(SelectMoveDestination(cid, warriors=warriors))
        actions.append(ResolveMove(warriors=1))

    for faction in factions:
        actions.append(SelectBattleTarget(faction.value))

    for card_id in card_ids:
        actions.extend([Craft(card_id), Mobilize(card_id), Train(card_id)])

    lookup = {action: i for i, action in enumerate(actions)}
    return ActionIndex(actions=actions, lookup=lookup)


def masked_alliance_policy(engine: RootEngine, model: AllianceNN, action_index: ActionIndex) -> torch.Tensor:
    """Return a masked categorical policy over a giant fixed Alliance action space."""

    encoded = AllianceNN.encode_leaf_state(engine.get_state(), observer=Faction.ALLIANCE)
    policy = model(encoded)
    logits = torch.log(policy.squeeze(0).clamp_min(1e-12))

    valid_actions = engine.get_valid_actions()
    valid_indices = [action_index.lookup[action] for action in valid_actions if action in action_index.lookup]

    masked_logits = torch.full_like(logits, float("-inf"))
    if valid_indices:
        masked_logits[valid_indices] = logits[valid_indices]
        masked_policy = torch.softmax(masked_logits, dim=-1)
        return masked_policy

    # Safety fallback for weird intermediate states.
    return torch.softmax(logits, dim=-1)


engine = RootEngine(seed=random.randint(1,100000), excluded_factions={Faction.VAGABOND}, marquise_ai_enabled=True, eyrie_ai_enabled=True)

action_index = build_alliance_action_index()
input = AllianceNN.encode_leaf_state(engine.get_state(), observer=Faction.ALLIANCE)
input_dim = input.numel()

alliance_policy_model = AllianceNN(input_dim=input_dim, action_dim=len(action_index.actions))


for i in range(50):
    input = AllianceNN.encode_leaf_state(engine.get_state(), observer=Faction.ALLIANCE)
    output = alliance_policy_model(input)
