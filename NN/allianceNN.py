from __future__ import annotations

from typing import Sequence

import torch
import torch.nn as nn

from root_engine.enums import Faction
from root_engine.models import GameState
from root_engine.observation import Observation, build_observation


class AllianceNN(nn.Module):
    """Policy network for the Woodland Alliance.

    Input should be a flattened state/observation vector of shape:
    - [input_dim] for a single position, or
    - [batch_size, input_dim] for a batch.

    Output:
    - policy: probability distribution across actions, shape [..., action_dim]
    """

    def __init__(self, input_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()

        self.backbone = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )

        self.policy_head = nn.Linear(hidden_dim, action_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 1:
            x = x.unsqueeze(0)

        features = self.backbone(x)
        return torch.softmax(self.policy_head(features), dim=-1)

    @staticmethod
    def encode_leaf_state(
        state: GameState,
        *,
        observer: Faction = Faction.ALLIANCE,
        device: torch.device | None = None,
        dtype: torch.dtype = torch.float32,
    ) -> torch.Tensor:
        """Convert a leaf node `GameState` into a model-ready tensor.

        This is a small baseline encoder to help wire MCTS/leaf-node inference.
        It uses only stable, visible features and can be expanded over time.
        """

        obs = build_observation(state, observer)
        return encode_observation(obs, observer=observer, device=device, dtype=dtype)


def encode_observation(
    obs: Observation,
    *,
    observer: Faction = Faction.ALLIANCE,
    device: torch.device | None = None,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Flatten an `Observation` into a 1D feature tensor.

    Current feature layout:
    [score_alliance,
     score_marquise, score_eyrie, score_vagabond,
     round_number,
     one-hot current_faction (4),
     officers,
     sympathy_in_supply,
     base_fox, base_rabbit, base_mouse,
     total_alliance_warriors_on_map,
     total_alliance_sympathy_on_map]
    """

    alliance_board = obs.factions[Faction.ALLIANCE]
    public = alliance_board.public_data

    faction_order: Sequence[Faction] = (
        Faction.MARQUISE,
        Faction.EYRIE,
        Faction.ALLIANCE,
        Faction.VAGABOND,
    )

    features: list[float] = []

    features.append(float(obs.scores[Faction.ALLIANCE]))
    for faction in faction_order:
        features.append(float(obs.scores[faction]))

    features.append(float(obs.round_number))

    for faction in faction_order:
        features.append(1.0 if obs.current_faction == faction else 0.0)

    features.append(float(public.get("officers", 0)))
    features.append(float(public.get("sympathy_in_supply", 0)))

    bases = public.get("bases", {})
    features.append(1.0 if bases.get("fox", False) else 0.0)
    features.append(1.0 if bases.get("rabbit", False) else 0.0)
    features.append(1.0 if bases.get("mouse", False) else 0.0)

    alliance_warriors = 0
    alliance_sympathy = 0
    for clearing in obs.clearings.values():
        alliance_warriors += clearing.warriors[Faction.ALLIANCE]
        alliance_sympathy += sum(1 for t in clearing.tokens[Faction.ALLIANCE] if t == "sympathy")

    features.append(float(alliance_warriors))
    features.append(float(alliance_sympathy))

    tensor = torch.tensor(features, dtype=dtype, device=device)
    return tensor
