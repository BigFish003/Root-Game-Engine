from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch

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
from root_engine.enums import BuildingType, Faction


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
