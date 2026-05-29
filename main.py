from __future__ import annotations
import math
import random
import copy
import argparse
from dataclasses import dataclass
from typing import Dict, Optional, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical

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


@dataclass(frozen=True)
class PPOConfig:
    total_updates: int = 25
    rollout_steps: int = 256
    max_episode_steps: int = 300
    ppo_epochs: int = 4
    minibatch_size: int = 64
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    learning_rate: float = 3e-4
    seed: int = 0
    checkpoint_path: str = "alliance_ppo.pt"


@dataclass
class PPORollout:
    observations: list[torch.Tensor]
    actions: list[int]
    log_probs: list[float]
    values: list[float]
    rewards: list[float]
    dones: list[bool]
    action_masks: list[torch.Tensor]

    def __init__(self) -> None:
        self.observations = []
        self.actions = []
        self.log_probs = []
        self.values = []
        self.rewards = []
        self.dones = []
        self.action_masks = []

    def __len__(self) -> int:
        return len(self.actions)

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

def valid_alliance_action_indices(valid_actions: list[Any], action_index: ActionIndex) -> list[int]:
    valid_indices = [
        action_index.lookup[action]
        for action in valid_actions
        if action in action_index.lookup
    ]
    if not valid_indices:
        raise ValueError(
            "No currently valid Alliance actions are represented in the action index"
        )
    return valid_indices


def alliance_action_mask(
    valid_actions: list[Any], action_index: ActionIndex, *, device: torch.device | None = None
) -> torch.Tensor:
    mask = torch.zeros(len(action_index.actions), dtype=torch.bool, device=device)
    mask[valid_alliance_action_indices(valid_actions, action_index)] = True
    return mask


def masked_alliance_logits(output: torch.Tensor, valid_actions: list[Any], action_index: ActionIndex) -> torch.Tensor:
    """Return policy logits with invalid Alliance actions set to ``-inf``."""

    action_dim = output.shape[-1]
    indices = torch.tensor(
        valid_alliance_action_indices(valid_actions, action_index),
        device=output.device,
        dtype=torch.long,
    )
    masked_logits = torch.full_like(output, float("-inf"))
    flat_output = output.reshape(-1, action_dim)
    flat_masked = masked_logits.reshape(-1, action_dim)
    flat_masked[:, indices] = flat_output[:, indices]
    return masked_logits


def masked_alliance_policy(output: torch.Tensor, valid_actions: list[Any], action_index: ActionIndex) -> torch.Tensor:
    """Return a new policy tensor with invalid Alliance actions masked out.

    ``AllianceNN`` returns raw policy logits, which may be negative. Invalid
    actions must therefore be set to negative infinity before normalizing; simply
    zeroing them can make an illegal action look better than every legal action.
    The returned tensor is a probability distribution over only the represented
    legal actions, and the input tensor is never mutated.
    """

    return torch.softmax(masked_alliance_logits(output, valid_actions, action_index), dim=-1)


def make_value_model(input_dim: int, hidden_dim: int = 256) -> nn.Module:
    return nn.Sequential(
        nn.Linear(input_dim, hidden_dim),
        nn.ReLU(),
        nn.Linear(hidden_dim, hidden_dim),
        nn.ReLU(),
        nn.Linear(hidden_dim, 1),
    )


def _new_training_engine(seed: int | None = None) -> RootEngine:
    return RootEngine(
        seed=seed,
        excluded_factions={Faction.VAGABOND},
        marquise_ai_enabled=True,
        marquise_ai_max_depth=1,
        marquise_ai_branch_factor=3,
        eyrie_ai_enabled=True,
        eyrie_ai_max_depth=1,
        eyrie_ai_branch_factor=3,
    )


def _score_reward(engine: RootEngine, previous_alliance_score: int) -> float:
    state = engine.get_state()
    reward = float(state.scores[Faction.ALLIANCE] - previous_alliance_score)
    if engine.is_terminal():
        reward += 10.0 if engine.get_winner() == Faction.ALLIANCE else -10.0
    return reward


def collect_ppo_rollout(
    policy_model: AllianceNN,
    value_model: nn.Module,
    action_index: ActionIndex,
    config: PPOConfig,
    *,
    device: torch.device,
    start_seed: int,
) -> tuple[PPORollout, float, int]:
    """Collect Alliance decisions against the built-in Marquise/Eyrie AIs."""

    rollout = PPORollout()
    episode_rewards: list[float] = []
    episode_reward = 0.0
    episode_steps = 0
    episodes_finished = 0
    engine = _new_training_engine(start_seed)

    while len(rollout) < config.rollout_steps:
        if engine.is_terminal() or episode_steps >= config.max_episode_steps:
            episode_rewards.append(episode_reward)
            episodes_finished += 1
            engine = _new_training_engine(start_seed + episodes_finished)
            episode_reward = 0.0
            episode_steps = 0

        observation = AllianceNN.encode_leaf_state(
            engine.get_state(), observer=Faction.ALLIANCE, device=device
        )
        valid_actions = engine.get_valid_actions()
        action_mask = alliance_action_mask(valid_actions, action_index, device=device)
        previous_alliance_score = engine.get_state().scores[Faction.ALLIANCE]

        with torch.no_grad():
            logits = policy_model(observation)
            masked_logits = logits.masked_fill(~action_mask.unsqueeze(0), float("-inf"))
            distribution = Categorical(logits=masked_logits)
            action_tensor = distribution.sample()
            log_prob = distribution.log_prob(action_tensor)
            value = value_model(observation).squeeze(-1)

        action_idx = int(action_tensor.item())
        engine.apply_action(action_index.actions[action_idx])
        episode_steps += 1

        reward = _score_reward(engine, previous_alliance_score)
        done = engine.is_terminal() or episode_steps >= config.max_episode_steps
        episode_reward += reward

        rollout.observations.append(observation.detach().cpu())
        rollout.actions.append(action_idx)
        rollout.log_probs.append(float(log_prob.item()))
        rollout.values.append(float(value.item()))
        rollout.rewards.append(reward)
        rollout.dones.append(done)
        rollout.action_masks.append(action_mask.detach().cpu())

    if episode_steps > 0:
        episode_rewards.append(episode_reward)
    return rollout, sum(episode_rewards) / max(len(episode_rewards), 1), episodes_finished


def _compute_gae(
    rollout: PPORollout,
    *,
    gamma: float,
    gae_lambda: float,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    advantages = [0.0 for _ in rollout.rewards]
    gae = 0.0
    for step in reversed(range(len(rollout.rewards))):
        next_value = 0.0 if step == len(rollout.rewards) - 1 else rollout.values[step + 1]
        next_non_terminal = 0.0 if rollout.dones[step] else 1.0
        delta = rollout.rewards[step] + gamma * next_value * next_non_terminal - rollout.values[step]
        gae = delta + gamma * gae_lambda * next_non_terminal * gae
        advantages[step] = gae

    advantages_tensor = torch.tensor(advantages, dtype=torch.float32, device=device)
    returns_tensor = advantages_tensor + torch.tensor(rollout.values, dtype=torch.float32, device=device)
    advantages_tensor = (advantages_tensor - advantages_tensor.mean()) / (advantages_tensor.std(unbiased=False) + 1e-8)
    return advantages_tensor, returns_tensor


def update_ppo(
    policy_model: AllianceNN,
    value_model: nn.Module,
    optimizer: torch.optim.Optimizer,
    rollout: PPORollout,
    config: PPOConfig,
    *,
    device: torch.device,
) -> dict[str, float]:
    observations = torch.stack(rollout.observations).to(device)
    actions = torch.tensor(rollout.actions, dtype=torch.long, device=device)
    old_log_probs = torch.tensor(rollout.log_probs, dtype=torch.float32, device=device)
    action_masks = torch.stack(rollout.action_masks).to(device)
    advantages, returns = _compute_gae(
        rollout, gamma=config.gamma, gae_lambda=config.gae_lambda, device=device
    )
    losses = {"policy": 0.0, "value": 0.0, "entropy": 0.0}
    batch_size = len(rollout)

    for _ in range(config.ppo_epochs):
        permutation = torch.randperm(batch_size, device=device)
        for start in range(0, batch_size, config.minibatch_size):
            batch_indices = permutation[start : start + config.minibatch_size]
            logits = policy_model(observations[batch_indices])
            masked_logits = logits.masked_fill(~action_masks[batch_indices], float("-inf"))
            distribution = Categorical(logits=masked_logits)
            new_log_probs = distribution.log_prob(actions[batch_indices])
            ratio = torch.exp(new_log_probs - old_log_probs[batch_indices])

            unclipped = ratio * advantages[batch_indices]
            clipped = torch.clamp(
                ratio, 1.0 - config.clip_epsilon, 1.0 + config.clip_epsilon
            ) * advantages[batch_indices]
            policy_loss = -torch.min(unclipped, clipped).mean()

            values = value_model(observations[batch_indices]).squeeze(-1)
            value_loss = F.mse_loss(values, returns[batch_indices])
            entropy = distribution.entropy().mean()
            loss = policy_loss + config.value_coef * value_loss - config.entropy_coef * entropy

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(
                list(policy_model.parameters()) + list(value_model.parameters()),
                config.max_grad_norm,
            )
            optimizer.step()

            losses["policy"] = float(policy_loss.item())
            losses["value"] = float(value_loss.item())
            losses["entropy"] = float(entropy.item())
    return losses


def train_alliance_ppo(config: PPOConfig | None = None, *, device: str | torch.device | None = None) -> tuple[AllianceNN, nn.Module]:
    """Train the Alliance policy with PPO against built-in Marquise/Eyrie AIs."""

    config = config or PPOConfig()
    torch.manual_seed(config.seed)
    random.seed(config.seed)
    torch_device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

    action_index = build_alliance_action_index()
    setup_engine = _new_training_engine(config.seed)
    encoded_state = AllianceNN.encode_leaf_state(
        setup_engine.get_state(), observer=Faction.ALLIANCE, device=torch_device
    )
    policy_model = AllianceNN(
        input_dim=encoded_state.numel(), action_dim=len(action_index.actions)
    ).to(torch_device)
    value_model = make_value_model(encoded_state.numel()).to(torch_device)
    optimizer = torch.optim.Adam(
        list(policy_model.parameters()) + list(value_model.parameters()),
        lr=config.learning_rate,
    )

    for update in range(1, config.total_updates + 1):
        rollout, mean_reward, finished = collect_ppo_rollout(
            policy_model,
            value_model,
            action_index,
            config,
            device=torch_device,
            start_seed=config.seed + update * 10_000,
        )
        losses = update_ppo(
            policy_model,
            value_model,
            optimizer,
            rollout,
            config,
            device=torch_device,
        )
        print(
            f"update={update:03d} steps={len(rollout)} episodes={finished} "
            f"mean_reward={mean_reward:.2f} policy_loss={losses['policy']:.3f} "
            f"value_loss={losses['value']:.3f} entropy={losses['entropy']:.3f}"
        )

    torch.save(
        {
            "policy_state_dict": policy_model.state_dict(),
            "value_state_dict": value_model.state_dict(),
            "config": config.__dict__,
            "action_count": len(action_index.actions),
            "input_dim": encoded_state.numel(),
        },
        config.checkpoint_path,
    )
    return policy_model, value_model

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train or demo the Alliance policy.")
    subparsers = parser.add_subparsers(dest="command")

    train_parser = subparsers.add_parser("train", help="Train AllianceNN with PPO")
    train_parser.add_argument("--updates", type=int, default=PPOConfig.total_updates)
    train_parser.add_argument("--rollout-steps", type=int, default=PPOConfig.rollout_steps)
    train_parser.add_argument("--max-episode-steps", type=int, default=PPOConfig.max_episode_steps)
    train_parser.add_argument("--ppo-epochs", type=int, default=PPOConfig.ppo_epochs)
    train_parser.add_argument("--minibatch-size", type=int, default=PPOConfig.minibatch_size)
    train_parser.add_argument("--learning-rate", type=float, default=PPOConfig.learning_rate)
    train_parser.add_argument("--seed", type=int, default=PPOConfig.seed)
    train_parser.add_argument("--checkpoint", default=PPOConfig.checkpoint_path)
    train_parser.add_argument("--device", default=None)

    demo_parser = subparsers.add_parser("demo", help="Run untrained policy demo games")
    demo_parser.add_argument("--games", type=int, default=5)

    parser.set_defaults(command="train")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.command == "demo":
        run_demo_games(args.games)
    else:
        train_alliance_ppo(
            PPOConfig(
                total_updates=args.updates,
                rollout_steps=args.rollout_steps,
                max_episode_steps=args.max_episode_steps,
                ppo_epochs=args.ppo_epochs,
                minibatch_size=args.minibatch_size,
                learning_rate=args.learning_rate,
                seed=args.seed,
                checkpoint_path=args.checkpoint,
            ),
            device=args.device,
        )
