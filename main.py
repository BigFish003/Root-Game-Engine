from __future__ import annotations
import math
import random
import copy
from dataclasses import dataclass
from typing import Dict, Optional, Any

import torch
from sympy.logic.inference import valid

from NN.allianceNN import AllianceNN
from root_engine.actions import (
    Build,
    Craft,
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

from state_renderer.render import state_renderer

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

    actions: list[Any] = [EndPhase()]

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

def masked_alliance_policy(output: torch.Tensor, valid_actions: list[Any], action_index: ActionIndex) -> torch.Tensor:
    """Return a new policy tensor with invalid Alliance actions masked out.

    ``AllianceNN`` returns raw policy logits, which may be negative. Invalid
    actions must therefore be set to negative infinity before normalizing; simply
    zeroing them can make an illegal action look better than every legal action.
    The returned tensor is a probability distribution over only the represented
    legal actions, and the input tensor is never mutated.
    """

    valid_indices = [
        action_index.lookup[action]
        for action in valid_actions
        if action in action_index.lookup
    ]

    if not valid_indices:
        raise ValueError(
            "No currently valid Alliance actions are represented in the action index"
        )

    action_dim = output.shape[-1]
    indices = torch.tensor(valid_indices, device=output.device, dtype=torch.long)

    masked_logits = torch.full_like(output, float("-inf"))
    flat_output = output.reshape(-1, action_dim)
    flat_masked = masked_logits.reshape(-1, action_dim)
    flat_masked[:, indices] = flat_output[:, indices]

    return torch.softmax(masked_logits, dim=-1)

def run_demo_games(game_count: int = 5) -> None:
    setup_engine = RootEngine(
        excluded_factions={Faction.VAGABOND},
        marquise_ai_enabled=True,
        eyrie_ai_enabled=True,
    )

    action_index = build_alliance_action_index()
    encoded_state = AllianceNN.encode_leaf_state(
        setup_engine.get_state(), observer=Faction.ALLIANCE
    )
    input_dim = encoded_state.numel()

    alliance_policy_model = AllianceNN(
        input_dim=input_dim, action_dim=len(action_index.actions)
    )

    render = state_renderer()
    for _ in range(game_count):
        engine = RootEngine(
            excluded_factions={Faction.VAGABOND},
            marquise_ai_enabled=True,
            eyrie_ai_enabled=True,
        )
        while not engine.is_terminal():
            encoded_state = AllianceNN.encode_leaf_state(
                engine.get_state(), observer=Faction.ALLIANCE
            )
            output = alliance_policy_model(encoded_state)

            valid_actions = engine.get_valid_actions()
            masked_output = masked_alliance_policy(output, valid_actions, action_index)
            best_action_idx = masked_output.argmax().item()
            best_action = action_index.actions[best_action_idx]


            print(best_action)
            render.render_board(
                engine.get_observation(Faction.ALLIANCE), output_path="game_state.png"
            )
            engine.apply_action(best_action)
        print(engine.get_state().scores)

if __name__ == "__main__":
    pass
