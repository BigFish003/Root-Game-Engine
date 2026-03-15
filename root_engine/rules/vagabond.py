"""Vagabond placeholders for extension."""

from __future__ import annotations

from ..actions import EndPhase
from ..models import GameState


def valid_actions(state: GameState) -> list:
    """TODO: Implement full Vagabond atomic action flow."""

    return [EndPhase()]
