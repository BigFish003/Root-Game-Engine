"""Woodland Alliance placeholders for extension."""

from __future__ import annotations

from ..actions import EndPhase
from ..enums import Faction
from ..models import GameState


def valid_actions(state: GameState) -> list:
    """TODO: Implement full Alliance birdsong/daylight/evening action tree."""

    return [EndPhase()]


def gain_supporter(state: GameState, card_id: int) -> bool:
    """Gain one supporter, respecting base-dependent stack capacity."""

    if not can_gain_supporter(state):
        state.discard_pile.append(card_id)
        return False
    state.alliance.supporters.append(card_id)
    return True


def can_gain_supporter(state: GameState) -> bool:
    """Supporters are capped at 5 when the Alliance has no bases."""

    has_any_base = any(state.alliance.bases.values())
    if has_any_base:
        return True
    return len(state.alliance.supporters) < 5


def legal_crafting_cards(state: GameState) -> list[int]:
    """Alliance crafts by activating sympathy tokens in Daylight."""

    from .crafting import legal_craft_cards

    return legal_craft_cards(state, state.alliance.hand, Faction.ALLIANCE)
