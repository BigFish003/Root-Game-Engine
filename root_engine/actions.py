"""Typed action objects consumed by the engine."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import BuildingType


@dataclass(frozen=True)
class Action:
    """Base class for all actions."""


@dataclass(frozen=True)
class EndDecision(Action):
    """End current atomic decision or pass where legal."""


@dataclass(frozen=True)
class EndPhase(Action):
    """Advance to next phase for current faction."""


@dataclass(frozen=True)
class ChooseClearing(Action):
    clearing_id: int


@dataclass(frozen=True)
class ChooseFaction(Action):
    faction: str


@dataclass(frozen=True)
class Recruit(Action):
    clearing_id: int


@dataclass(frozen=True)
class Build(Action):
    clearing_id: int
    building_type: BuildingType


@dataclass(frozen=True)
class SelectMoveSource(Action):
    clearing_id: int


@dataclass(frozen=True)
class SelectMoveDestination(Action):
    clearing_id: int


@dataclass(frozen=True)
class ResolveMove(Action):
    warriors: int = 1


@dataclass(frozen=True)
class SelectBattleClearing(Action):
    clearing_id: int


@dataclass(frozen=True)
class SelectBattleTarget(Action):
    target_faction: str


@dataclass(frozen=True)
class Craft(Action):
    card_id: int


@dataclass(frozen=True)
class AddToDecree(Action):
    card_id: int
    column: str


@dataclass(frozen=True)
class FallIntoTurmoil(Action):
    """Resolve forced turmoil when decree cannot be completed."""
