"""Woodland Alliance legal action generation and birdsong actions."""

from __future__ import annotations

from ..actions import EndPhase, Revolt, SpreadSympathy
from ..enums import BuildingType, Faction, Phase, Suit, TokenType
from ..models import GameState


def valid_actions(state: GameState) -> list:
    """Generate Alliance actions, with full Birdsong Revolt/Spread Sympathy."""

    if state.turn.phase != Phase.BIRDSONG:
        return [EndPhase()]
    actions: list = []
    actions.extend(Revolt(clearing_id=cid) for cid in _legal_revolt_clearings(state))
    actions.extend(SpreadSympathy(clearing_id=cid) for cid in _legal_sympathy_clearings(state))
    actions.append(EndPhase())
    return actions


def apply_revolt(state: GameState, action: Revolt) -> None:
    clearing = state.board.clearings[action.clearing_id]
    suit = clearing.suit
    if suit not in {Suit.FOX, Suit.RABBIT, Suit.MOUSE}:
        raise ValueError("Cannot revolt in bird-suit clearing")
    if state.alliance.bases[suit]:
        raise ValueError("Matching base is already built")
    if TokenType.SYMPATHY not in state.board.tokens[action.clearing_id][Faction.ALLIANCE]:
        raise ValueError("Can only revolt in a sympathetic clearing")
    if not _can_spend_supporters(state, suit, 2):
        raise ValueError("Not enough matching supporters to revolt")

    _spend_supporters(state, suit, 2)
    _remove_enemy_pieces_and_score(state, action.clearing_id)
    state.board.buildings[action.clearing_id][Faction.ALLIANCE].append(BuildingType.BASE)
    state.alliance.bases[suit] = True

    # Alliance warrior supply is currently inferred from warriors on board + officers.
    remaining_supply = _alliance_warriors_in_supply(state)
    warriors_to_place = min(remaining_supply, _count_sympathy_of_suit(state, suit))
    state.board.warriors[action.clearing_id][Faction.ALLIANCE] += warriors_to_place

    if _alliance_warriors_in_supply(state) > 0:
        state.alliance.officers += 1


def apply_spread_sympathy(state: GameState, action: SpreadSympathy) -> None:
    if TokenType.SYMPATHY in state.board.tokens[action.clearing_id][Faction.ALLIANCE]:
        raise ValueError("Clearing already sympathetic")
    if action.clearing_id not in _legal_sympathy_clearings(state):
        raise ValueError("Clearing is not eligible for sympathy")
    if state.alliance.sympathy_in_supply <= 0:
        raise ValueError("No sympathy tokens remaining")
    suit = state.board.clearings[action.clearing_id].suit
    base_cost = _sympathy_supporter_cost(state)
    martial_law_cost = 1 if _has_martial_law(state, action.clearing_id) else 0
    total_cost = base_cost + martial_law_cost
    if not _can_spend_supporters(state, suit, total_cost):
        raise ValueError("Not enough supporters to spread sympathy")
    _spend_supporters(state, suit, total_cost)
    state.board.tokens[action.clearing_id][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    state.alliance.sympathy_in_supply -= 1
    state.scores[Faction.ALLIANCE] += _sympathy_vp_reward(state)


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


def _legal_revolt_clearings(state: GameState) -> list[int]:
    clearings: list[int] = []
    for cid, clearing in state.board.clearings.items():
        suit = clearing.suit
        if suit not in {Suit.FOX, Suit.RABBIT, Suit.MOUSE}:
            continue
        if state.alliance.bases[suit]:
            continue
        if TokenType.SYMPATHY not in state.board.tokens[cid][Faction.ALLIANCE]:
            continue
        if _can_spend_supporters(state, suit, 2):
            clearings.append(cid)
    return clearings


def _legal_sympathy_clearings(state: GameState) -> list[int]:
    sympathetic = {
        cid
        for cid in state.board.clearings
        if TokenType.SYMPATHY in state.board.tokens[cid][Faction.ALLIANCE]
    }
    if sympathetic:
        candidates = {
            adjacent
            for cid in sympathetic
            for adjacent in state.board.clearings[cid].adjacent_clearings
            if adjacent not in sympathetic
        }
    else:
        candidates = set(state.board.clearings.keys())
    legal: list[int] = []
    for cid in sorted(candidates):
        suit = state.board.clearings[cid].suit
        cost = _sympathy_supporter_cost(state) + (1 if _has_martial_law(state, cid) else 0)
        if _can_spend_supporters(state, suit, cost):
            legal.append(cid)
    return legal


def _has_martial_law(state: GameState, clearing_id: int) -> bool:
    return any(
        faction != Faction.ALLIANCE and warriors >= 3
        for faction, warriors in state.board.warriors[clearing_id].items()
    )


def _supporter_matches_suit(state: GameState, card_id: int, suit: Suit) -> bool:
    card_suit = state.cards[card_id].suit
    return card_suit == suit or card_suit == Suit.BIRD


def _can_spend_supporters(state: GameState, suit: Suit, amount: int) -> bool:
    if amount <= 0:
        return True
    return sum(1 for card_id in state.alliance.supporters if _supporter_matches_suit(state, card_id, suit)) >= amount


def _spend_supporters(state: GameState, suit: Suit, amount: int) -> None:
    remaining = amount
    for idx in range(len(state.alliance.supporters) - 1, -1, -1):
        card_id = state.alliance.supporters[idx]
        if _supporter_matches_suit(state, card_id, suit):
            state.discard_pile.append(state.alliance.supporters.pop(idx))
            remaining -= 1
            if remaining == 0:
                return
    raise ValueError("Insufficient supporters to spend")


def _remove_enemy_pieces_and_score(state: GameState, clearing_id: int) -> None:
    for faction in Faction:
        if faction == Faction.ALLIANCE:
            continue
        state.board.warriors[clearing_id][faction] = 0
        removed_buildings = len(state.board.buildings[clearing_id][faction])
        removed_tokens = len(state.board.tokens[clearing_id][faction])
        state.board.buildings[clearing_id][faction].clear()
        state.board.tokens[clearing_id][faction].clear()
        state.scores[Faction.ALLIANCE] += removed_buildings + removed_tokens


def _count_sympathy_of_suit(state: GameState, suit: Suit) -> int:
    return sum(
        1
        for cid, clearing in state.board.clearings.items()
        if clearing.suit == suit and TokenType.SYMPATHY in state.board.tokens[cid][Faction.ALLIANCE]
    )


def _alliance_warriors_in_supply(state: GameState) -> int:
    placed = sum(state.board.warriors[cid][Faction.ALLIANCE] for cid in state.board.clearings)
    placed += state.alliance.officers
    return max(0, 10 - placed)


def _sympathy_supporter_cost(state: GameState) -> int:
    tokens_on_map = _sympathy_tokens_on_map(state)
    track = [1, 1, 1, 2, 2, 2, 3, 3, 3, 3]
    idx = min(tokens_on_map, len(track) - 1)
    return track[idx]


def _sympathy_vp_reward(state: GameState) -> int:
    tokens_on_map = _sympathy_tokens_on_map(state)
    rewards = [0, 1, 1, 1, 2, 2, 3, 4, 4, 4]
    idx = min(tokens_on_map - 1, len(rewards) - 1)
    return rewards[max(idx, 0)]


def _sympathy_tokens_on_map(state: GameState) -> int:
    return sum(
        1
        for cid in state.board.clearings
        if TokenType.SYMPATHY in state.board.tokens[cid][Faction.ALLIANCE]
    )
