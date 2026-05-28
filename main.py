from __future__ import annotations

import argparse
import copy
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import torch
import torch.nn.functional as F

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
from root_engine.enums import BuildingType, Faction, Phase, TokenType

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
    """Build the fixed action vocabulary used by the Alliance policy head."""

    clearings = range(1, 13)
    factions = (Faction.MARQUISE, Faction.EYRIE, Faction.VAGABOND)
    card_ids = range(1, 55)

    actions: list[Any] = [EndPhase(), EndDecision(), ResolveMove(warriors=1)]

    for cid in clearings:
        actions.extend(
            [
                Recruit(cid),
                Revolt(cid),
                SpreadSympathy(cid),
                Organize(cid),
                SelectMoveSource(cid),
                SelectMoveDestination(cid),
                SelectBattleClearing(cid),
                Build(cid, BuildingType.BASE),
            ]
        )

    for faction in factions:
        actions.append(SelectBattleTarget(faction.value))

    for card_id in card_ids:
        actions.extend([Craft(card_id), Mobilize(card_id), Train(card_id)])

    lookup = {action: i for i, action in enumerate(actions)}
    return ActionIndex(actions=actions, lookup=lookup)


def masked_alliance_policy(
    output: torch.Tensor, valid_actions: list[Any], action_index: ActionIndex
) -> torch.Tensor:
    """Return a new policy tensor with invalid Alliance actions masked out.

    ``AllianceNN`` already returns a probability distribution, so masking is most
    direct as a pure tensor operation: clone the model output, zero every action
    that is not currently legal, and renormalize the remaining legal actions.
    The input tensor is never mutated.
    """

    valid_indices = [
        action_index.lookup[action]
        for action in valid_actions
        if action in action_index.lookup
    ]
    masked_output = torch.zeros_like(output)

    if not valid_indices:
        # Safety fallback for weird intermediate states or an incomplete action index.
        return output.clone()

    action_dim = output.shape[-1]
    indices = torch.tensor(valid_indices, device=output.device, dtype=torch.long)
    flat_output = output.reshape(-1, action_dim)
    flat_masked = masked_output.reshape(-1, action_dim)
    flat_masked[:, indices] = flat_output[:, indices]

    normalizer = flat_masked.sum(dim=-1, keepdim=True)
    normalized = torch.where(
        normalizer > 0, flat_masked / normalizer.clamp_min(1e-12), flat_output
    )

    return normalized.reshape_as(output)


def alliance_action_score(action: Any, state: Any) -> float:
    """Cheap expert heuristic for imitation training.

    This is intentionally simple and fast: it gives the model a reasonable first
    policy without running expensive MCTS. After training, inference is just one
    neural-network forward pass plus the legal-action mask.
    """

    score = float(state.scores[Faction.ALLIANCE] * 10)

    if isinstance(action, Revolt):
        return score + 100 + _enemy_piece_count(state, action.clearing_id) * 8
    if isinstance(action, SpreadSympathy):
        return score + 70 + _sympathy_pressure_score(state, action.clearing_id)
    if isinstance(action, Organize):
        return score + 62 + _sympathy_pressure_score(state, action.clearing_id)
    if isinstance(action, Train):
        return score + 54 + max(0, 4 - state.alliance.officers) * 5
    if isinstance(action, Craft):
        return score + 45 + state.cards[action.card_id].vp_on_craft * 12
    if isinstance(action, Mobilize):
        return score + 35 + _supporter_need_score(state)
    if isinstance(action, Recruit):
        return score + 30 + _base_defense_need(state, action.clearing_id)
    if isinstance(action, SelectBattleClearing):
        return score + 25 + _enemy_piece_count(state, action.clearing_id) * 4
    if isinstance(action, SelectBattleTarget):
        return score + 22
    if isinstance(action, SelectMoveSource):
        return score + 16 + state.board.warriors[action.clearing_id][Faction.ALLIANCE]
    if isinstance(action, SelectMoveDestination):
        return score + 18 + _sympathy_pressure_score(state, action.clearing_id) * 0.5
    if isinstance(action, EndDecision):
        return score - 5
    if isinstance(action, EndPhase):
        phase_penalty = 22 if state.turn.phase in (Phase.BIRDSONG, Phase.DAYLIGHT) else 8
        return score - phase_penalty
    return score


def _enemy_piece_count(state: Any, clearing_id: int) -> int:
    return sum(
        state.board.warriors[clearing_id].get(faction, 0)
        + len(state.board.buildings[clearing_id].get(faction, []))
        + len(state.board.tokens[clearing_id].get(faction, []))
        for faction in (Faction.MARQUISE, Faction.EYRIE, Faction.VAGABOND)
    )


def _sympathy_pressure_score(state: Any, clearing_id: int) -> float:
    clearing = state.board.clearings[clearing_id]
    adjacent_sympathy = sum(
        1
        for neighbor_id in clearing.adjacent_clearings
        if TokenType.SYMPATHY in state.board.tokens[neighbor_id][Faction.ALLIANCE]
    )
    enemy_warriors = sum(
        state.board.warriors[clearing_id].get(faction, 0)
        for faction in (Faction.MARQUISE, Faction.EYRIE)
    )
    return adjacent_sympathy * 4 + enemy_warriors * 1.5 + clearing.building_slots


def _supporter_need_score(state: Any) -> float:
    bases_built = 3 - state.alliance.bases_in_supply
    supporter_soft_cap = 5 if bases_built == 0 else 54
    room = max(0, supporter_soft_cap - len(state.alliance.supporters))
    return min(12, room * 2)


def _base_defense_need(state: Any, clearing_id: int) -> float:
    has_base = BuildingType.BASE in state.board.buildings[clearing_id][Faction.ALLIANCE]
    if not has_base:
        return 0.0
    alliance_warriors = state.board.warriors[clearing_id][Faction.ALLIANCE]
    enemy_warriors = sum(
        state.board.warriors[clearing_id].get(faction, 0)
        for faction in (Faction.MARQUISE, Faction.EYRIE)
    )
    return 15 + max(0, enemy_warriors - alliance_warriors) * 4


def choose_expert_action(valid_actions: list[Any], state: Any) -> Any:
    return max(valid_actions, key=lambda action: alliance_action_score(action, state))


def choose_model_action(
    model: AllianceNN, engine: RootEngine, action_index: ActionIndex, *, device: torch.device
) -> Any:
    model.eval()
    with torch.no_grad():
        encoded = AllianceNN.encode_leaf_state(
            engine.get_state(), observer=Faction.ALLIANCE, device=device
        )
        output = model(encoded)
        masked_output = masked_alliance_policy(output, engine.get_valid_actions(), action_index)
        best_action_idx = masked_output.argmax(dim=-1).item()
    return action_index.actions[best_action_idx]


def collect_imitation_examples(
    *, games: int, max_alliance_decisions: int, seed: int, action_index: ActionIndex
) -> tuple[torch.Tensor, torch.Tensor]:
    examples: list[torch.Tensor] = []
    labels: list[int] = []

    for game_number in range(games):
        engine = RootEngine(
            seed=seed + game_number,
            excluded_factions={Faction.VAGABOND},
            marquise_ai_enabled=True,
            marquise_ai_max_depth=1,
            marquise_ai_branch_factor=4,
            eyrie_ai_enabled=True,
            eyrie_ai_max_depth=1,
            eyrie_ai_branch_factor=4,
        )
        alliance_decisions = 0
        while not engine.is_terminal() and alliance_decisions < max_alliance_decisions:
            state = engine.get_state()
            if state.turn.current_faction != Faction.ALLIANCE:
                break

            valid_actions = engine.get_valid_actions()
            indexed_actions = [action for action in valid_actions if action in action_index.lookup]
            if not indexed_actions:
                engine.apply_action(random.choice(valid_actions))
                continue

            expert_action = choose_expert_action(indexed_actions, state)
            examples.append(AllianceNN.encode_leaf_state(state, observer=Faction.ALLIANCE))
            labels.append(action_index.lookup[expert_action])
            engine.apply_action(expert_action)
            alliance_decisions += 1

    if not examples:
        raise RuntimeError("No Alliance training examples were collected")

    return torch.stack(examples), torch.tensor(labels, dtype=torch.long)


def train_fast_alliance_policy(args: argparse.Namespace) -> None:
    torch.manual_seed(args.seed)
    random.seed(args.seed)

    action_index = build_alliance_action_index()
    inputs, targets = collect_imitation_examples(
        games=args.games,
        max_alliance_decisions=args.max_alliance_decisions,
        seed=args.seed,
        action_index=action_index,
    )

    model = AllianceNN(input_dim=inputs.shape[-1], action_dim=len(action_index.actions))
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    for epoch in range(1, args.epochs + 1):
        permutation = torch.randperm(inputs.shape[0])
        epoch_loss = 0.0
        correct = 0

        for start in range(0, inputs.shape[0], args.batch_size):
            batch_idx = permutation[start : start + args.batch_size]
            batch_inputs = inputs[batch_idx]
            batch_targets = targets[batch_idx]

            optimizer.zero_grad()
            probabilities = model(batch_inputs).clamp_min(1e-9)
            loss = F.nll_loss(probabilities.log(), batch_targets)
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item() * batch_inputs.shape[0]
            correct += (probabilities.argmax(dim=-1) == batch_targets).sum().item()

        print(
            f"epoch={epoch} examples={inputs.shape[0]} "
            f"loss={epoch_loss / inputs.shape[0]:.4f} acc={correct / inputs.shape[0]:.3f}"
        )

    checkpoint_path = Path(args.checkpoint)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_dim": inputs.shape[-1],
            "action_dim": len(action_index.actions),
            "seed": args.seed,
        },
        checkpoint_path,
    )
    print(f"saved {checkpoint_path}")

    if args.eval_games:
        evaluate_policy(model, action_index, games=args.eval_games, seed=args.seed + 10_000)


def load_policy(checkpoint: str, action_index: ActionIndex) -> AllianceNN:
    saved = torch.load(checkpoint, map_location="cpu")
    model = AllianceNN(input_dim=saved["input_dim"], action_dim=len(action_index.actions))
    if saved["action_dim"] != len(action_index.actions):
        raise ValueError("Checkpoint action dimension does not match this action index")
    model.load_state_dict(saved["model_state_dict"])
    return model


def evaluate_policy(
    model: AllianceNN, action_index: ActionIndex, *, games: int, seed: int, render_output: str | None = None
) -> None:
    scores: list[int] = []
    wins = 0
    last_engine: RootEngine | None = None

    for game_number in range(games):
        engine = RootEngine(
            seed=seed + game_number,
            excluded_factions={Faction.VAGABOND},
            marquise_ai_enabled=True,
            eyrie_ai_enabled=True,
        )
        steps = 0
        while not engine.is_terminal() and steps < 2_000:
            if engine.get_state().turn.current_faction != Faction.ALLIANCE:
                break
            action = choose_model_action(model, engine, action_index, device=torch.device("cpu"))
            engine.apply_action(action)
            steps += 1

        score = engine.get_state().scores[Faction.ALLIANCE]
        scores.append(score)
        wins += int(engine.get_winner() == Faction.ALLIANCE if engine.is_terminal() else False)
        last_engine = engine

    avg_score = sum(scores) / len(scores)
    print(f"eval_games={games} avg_alliance_score={avg_score:.2f} wins={wins}/{games}")

    if render_output and last_engine is not None:
        renderer = state_renderer()
        renderer.render_board(last_engine.get_observation(Faction.ALLIANCE), render_output)
        print(f"rendered {render_output}")


def run_policy(args: argparse.Namespace) -> None:
    action_index = build_alliance_action_index()
    if args.checkpoint:
        model = load_policy(args.checkpoint, action_index)
    else:
        probe_engine = RootEngine(seed=args.seed, excluded_factions={Faction.VAGABOND})
        input_dim = AllianceNN.encode_leaf_state(
            probe_engine.get_state(), observer=Faction.ALLIANCE
        ).numel()
        model = AllianceNN(input_dim=input_dim, action_dim=len(action_index.actions))
    evaluate_policy(
        model,
        action_index,
        games=args.games,
        seed=args.seed,
        render_output=args.render_output,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train or run a fast Woodland Alliance policy")
    subparsers = parser.add_subparsers(dest="command")

    train_parser = subparsers.add_parser("train", help="train a quick imitation policy")
    train_parser.add_argument("--games", type=int, default=40)
    train_parser.add_argument("--max-alliance-decisions", type=int, default=120)
    train_parser.add_argument("--epochs", type=int, default=8)
    train_parser.add_argument("--batch-size", type=int, default=64)
    train_parser.add_argument("--lr", type=float, default=3e-4)
    train_parser.add_argument("--seed", type=int, default=7)
    train_parser.add_argument("--checkpoint", default="alliance_policy.pt")
    train_parser.add_argument("--eval-games", type=int, default=5)
    train_parser.set_defaults(func=train_fast_alliance_policy)

    run_parser = subparsers.add_parser("run", help="run/evaluate a saved policy")
    run_parser.add_argument("--checkpoint")
    run_parser.add_argument("--games", type=int, default=1)
    run_parser.add_argument("--seed", type=int, default=7)
    run_parser.add_argument("--render-output", default="game_state.png")
    run_parser.set_defaults(func=run_policy)

    args = parser.parse_args()
    if args.command is None:
        args = parser.parse_args(["train"])
    return args


if __name__ == "__main__":
    parsed_args = parse_args()
    parsed_args.func(parsed_args)
