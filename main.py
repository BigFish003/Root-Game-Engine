from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from root_engine.engine import RootEngine
from root_engine.enums import Faction


@dataclass
class MCTSNode:
    engine: RootEngine
    root_faction: Faction
    action_taken: object | None = None
    parent: "MCTSNode | None" = None
    children: list["MCTSNode"] = field(default_factory=list)
    untried_actions: list[object] = field(default_factory=list)
    visits: int = 0
    value_sum: float = 0.0

    def __post_init__(self) -> None:
        if not self.untried_actions:
            self.untried_actions = list(self.engine.get_valid_actions())

    @property
    def average_value(self) -> float:
        if self.visits == 0:
            return 0.0
        return self.value_sum / self.visits

    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0

    def best_uct_child(self, exploration: float) -> "MCTSNode":
        log_parent = math.log(max(1, self.visits))

        def uct_score(child: MCTSNode) -> float:
            exploitation = child.average_value
            exploration_bonus = exploration * math.sqrt(log_parent / max(1, child.visits))
            return exploitation + exploration_bonus

        return max(self.children, key=uct_score)


class MCTSAgent:
    def __init__(
        self,
        iterations: int = 400,
        max_rollout_steps: int = 60,
        exploration: float = math.sqrt(2.0),
        rng_seed: int | None = None,
    ) -> None:
        self.iterations = iterations
        self.max_rollout_steps = max_rollout_steps
        self.exploration = exploration
        self.rng = random.Random(rng_seed)

    def choose_action(self, engine: RootEngine, root_faction: Faction) -> object:
        root = MCTSNode(engine=engine.clone(), root_faction=root_faction)
        if not root.untried_actions:
            raise RuntimeError("No valid actions available at root")

        for _ in range(self.iterations):
            node = self._select(root)
            node = self._expand(node)
            reward = self._rollout(node)
            self._backpropagate(node, reward)

        best_child = max(root.children, key=lambda child: child.visits)
        return best_child.action_taken

    def _select(self, node: MCTSNode) -> MCTSNode:
        while node.children and node.is_fully_expanded() and not node.engine.is_terminal():
            node = node.best_uct_child(self.exploration)
        return node

    def _expand(self, node: MCTSNode) -> MCTSNode:
        if node.engine.is_terminal() or not node.untried_actions:
            return node

        action = node.untried_actions.pop(self.rng.randrange(len(node.untried_actions)))
        next_engine = node.engine.clone()
        next_engine.apply_action(action)

        child = MCTSNode(
            engine=next_engine,
            root_faction=node.root_faction,
            action_taken=action,
            parent=node,
        )
        node.children.append(child)
        return child

    def _rollout(self, node: MCTSNode) -> float:
        sim = node.engine.clone()

        for _ in range(self.max_rollout_steps):
            if sim.is_terminal():
                break
            actions = sim.get_valid_actions()
            if not actions:
                break
            sim.apply_action(self.rng.choice(actions))

        return self._evaluate(sim, node.root_faction)

    def _evaluate(self, engine: RootEngine, root_faction: Faction) -> float:
        state = engine.get_state()
        root_score = state.scores[root_faction]
        opponent_scores = [score for faction, score in state.scores.items() if faction != root_faction]
        best_opponent = max(opponent_scores, default=0)
        return float(root_score - best_opponent)

    def _backpropagate(self, node: MCTSNode, reward: float) -> None:
        cursor: MCTSNode | None = node
        while cursor is not None:
            cursor.visits += 1
            cursor.value_sum += reward
            cursor = cursor.parent


def run_demo() -> None:
    engine = RootEngine(seed=7, excluded_factions={Faction.VAGABOND})
    root_faction = engine.get_state().turn.current_faction
    agent = MCTSAgent(iterations=500, max_rollout_steps=80, rng_seed=7)

    action = agent.choose_action(engine, root_faction)
    print(f"MCTS selected action for {root_faction.value}: {action}")

    engine.apply_action(action)


if __name__ == "__main__":
    run_demo()
