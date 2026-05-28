"""Helpers for moving cardboard pieces between the map and supplies."""

from __future__ import annotations

from ..enums import BuildingType, Faction, Suit, TokenType
from ..models import GameState


def return_building_to_supply(
    state: GameState,
    faction: Faction,
    building: BuildingType,
    clearing_id: int,
) -> None:
    """Return a removed building to its faction supply track."""

    if faction == Faction.MARQUISE and building in state.marquise.buildings_in_supply:
        state.marquise.buildings_in_supply[building] += 1
    elif faction == Faction.EYRIE and building == BuildingType.ROOST:
        state.eyrie.roosts_in_supply += 1
    elif faction == Faction.ALLIANCE and building == BuildingType.BASE:
        suit = state.board.clearings[clearing_id].suit
        if suit in {Suit.FOX, Suit.RABBIT, Suit.MOUSE}:
            state.alliance.bases[suit] = False


def return_token_to_supply(state: GameState, faction: Faction, token: TokenType) -> None:
    """Return a removed token to its faction supply track when one is tracked."""

    if faction == Faction.ALLIANCE and token == TokenType.SYMPATHY:
        state.alliance.sympathy_in_supply += 1
