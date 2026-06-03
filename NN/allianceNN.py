from __future__ import annotations

import torch
import torch.nn as nn

from root_engine.enums import Faction
from root_engine.models import GameState
from root_engine.observation import build_observation

from NN.alliance_features import encode_observation


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
        return self.policy_head(features)

    @staticmethod
    def encode_leaf_state(
        state: GameState,
        *,
        observer: Faction = Faction.ALLIANCE,
        device: torch.device | None = None,
        dtype: torch.dtype = torch.float32,
    ) -> torch.Tensor:
        """Convert a leaf node `GameState` into a model-ready observation tensor.

        The encoder intentionally works from `build_observation` so it only consumes
        information visible to the requested observer. For the Alliance this means
        all public map/faction state plus the Alliance's own hand and supporter row,
        while hidden enemy hands and the draw pile are represented only by public
        counts or omitted entirely.
        """

        obs = build_observation(state, observer)
        return encode_observation(obs, observer=observer, device=device, dtype=dtype)


