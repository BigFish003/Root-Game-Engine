import pytest

pytest.importorskip("torch")
import torch

from main import build_alliance_action_index, masked_alliance_policy
from root_engine.actions import EndPhase, SelectMoveDestination, SpreadSympathy


def test_masked_alliance_policy_never_prefers_zeroed_invalid_logits():
    action_index = build_alliance_action_index()
    valid_actions = [EndPhase(), SpreadSympathy(clearing_id=2)]
    illegal_action = SelectMoveDestination(clearing_id=3, warriors=6)

    logits = torch.full((1, len(action_index.actions)), -10.0)
    logits[0, action_index.lookup[illegal_action]] = 0.0
    logits[0, action_index.lookup[SpreadSympathy(clearing_id=2)]] = -1.0
    logits[0, action_index.lookup[EndPhase()]] = -2.0

    masked_policy = masked_alliance_policy(logits, valid_actions, action_index)
    best_action = action_index.actions[masked_policy.argmax().item()]

    assert best_action == SpreadSympathy(clearing_id=2)
    assert best_action in valid_actions
    assert masked_policy[0, action_index.lookup[illegal_action]].item() == 0.0


def test_masked_alliance_policy_rejects_unrepresented_valid_actions():
    action_index = build_alliance_action_index()
    logits = torch.zeros((1, len(action_index.actions)))

    with pytest.raises(ValueError, match="No currently valid Alliance actions"):
        masked_alliance_policy(
            logits,
            [SelectMoveDestination(clearing_id=3, warriors=99)],
            action_index,
        )
