"""Woodland Alliance placeholders for extension."""

from __future__ import annotations

from ..actions import EndPhase
from ..models import GameState


def valid_actions(state: GameState) -> list:
    """TODO: Implement full Alliance birdsong/daylight/evening action tree."""

    return [EndPhase()]
