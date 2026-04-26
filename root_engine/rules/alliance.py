"""Woodland Alliance legal action generation and action resolution."""

from __future__ import annotations

from ..actions import (
    Craft,
    EndDecision,
    EndPhase,
    Mobilize,
    Organize,
    Recruit,
    Revolt,
    SelectBattleClearing,
    SelectBattleTarget,
    SelectMoveDestination,
    SelectMoveSource,
    SpreadSympathy,
    Train,
)
from ..enums import BuildingType, CardTag, DecisionType, Faction, Phase, Suit, TokenType
from ..models import GameState
from .combat import legal_battle_clearings, legal_battle_targets, resolve_basic_battle
from .crafting import legal_craft_cards
from .movement import legal_move_destinations, legal_move_sources


def valid_actions(state: GameState) -> list:
    """Generate Alliance legal actions for all phases."""

    if state.turn.phase == Phase.BIRDSONG:
        actions: list = []
        actions.extend(Revolt(clearing_id=cid) for cid in _legal_revolt_clearings(state))
        actions.extend(SpreadSympathy(clearing_id=cid) for cid in _legal_sympathy_clearings(state))
        actions.append(EndPhase())
        return actions

    if state.turn.phase == Phase.DAYLIGHT:
        actions: list = [EndPhase()]
        if state.alliance.crafting_window_open:
            actions.extend(Craft(card_id) for card_id in legal_crafting_cards(state))
        actions.extend(Mobilize(card_id=card_id) for card_id in state.alliance.hand)
        actions.extend(Train(card_id=card_id) for card_id in _legal_train_cards(state))
        return actions

    ctx = state.decision_context
    if state.alliance.military_ops_used >= state.alliance.officers:
        return [EndPhase()]
    if ctx.decision_type == DecisionType.MAIN_ACTION:
        actions = [EndPhase()]
        actions.extend(SelectMoveSource(cid) for cid in legal_move_sources(state, Faction.ALLIANCE))
        actions.extend(SelectBattleClearing(cid) for cid in legal_battle_clearings(state, Faction.ALLIANCE))
        actions.extend(Recruit(clearing_id=cid) for cid in _legal_evening_recruit_clearings(state))
        actions.extend(Organize(clearing_id=cid) for cid in _legal_organize_clearings(state))
        return actions
    if ctx.decision_type == DecisionType.SELECT_MOVE_DESTINATION and ctx.selected_source is not None:
        return [
            SelectMoveDestination(cid)
            for cid in legal_move_destinations(state, Faction.ALLIANCE, ctx.selected_source)
        ] + [EndDecision()]
    if ctx.decision_type == DecisionType.SELECT_BATTLE_TARGET and ctx.selected_battle_clearing is not None:
        return [
            SelectBattleTarget(f.value)
            for f in legal_battle_targets(state, Faction.ALLIANCE, ctx.selected_battle_clearing)
        ] + [EndDecision()]
    return [EndDecision()]


def apply_craft(state: GameState, action: Craft) -> None:
    if state.turn.phase != Phase.DAYLIGHT:
        raise ValueError("Craft can only be taken in Daylight")
    if action.card_id not in state.alliance.hand:
        raise ValueError("Card not in hand")
    if action.card_id not in legal_crafting_cards(state):
        raise ValueError("Card cannot be crafted with available sympathy")
    if not state.alliance.crafting_window_open:
        raise ValueError("Crafting is only available at the start of Daylight")
    card = state.cards[action.card_id]
    state.alliance.hand.remove(action.card_id)
    if card.vp_on_craft > 0:
        state.scores[Faction.ALLIANCE] += card.vp_on_craft
    if card.name.startswith("Favor of the"):
        _resolve_favor(state, card.suit)
    if CardTag.PERSISTENT_EFFECT in card.tags:
        state.alliance.crafted_effects.append(card.name)
    else:
        state.discard_pile.append(action.card_id)


def apply_mobilize(state: GameState, action: Mobilize) -> None:
    if state.turn.phase != Phase.DAYLIGHT:
        raise ValueError("Mobilize can only be taken in Daylight")
    if action.card_id not in state.alliance.hand:
        raise ValueError("Card not in hand")
    state.alliance.hand.remove(action.card_id)
    gain_supporter(state, action.card_id)
    state.alliance.crafting_window_open = False


def apply_train(state: GameState, action: Train) -> None:
    if state.turn.phase != Phase.DAYLIGHT:
        raise ValueError("Train can only be taken in Daylight")
    if action.card_id not in state.alliance.hand:
        raise ValueError("Card not in hand")
    if action.card_id not in _legal_train_cards(state):
        raise ValueError("Train card suit must match a built base")
    if _alliance_warriors_in_supply(state) <= 0:
        raise ValueError("No Alliance warriors in supply to train")
    state.alliance.hand.remove(action.card_id)
    state.discard_pile.append(action.card_id)
    state.alliance.officers += 1
    state.alliance.crafting_window_open = False


def apply_move_source(state: GameState, action: SelectMoveSource) -> None:
    state.decision_context.decision_type = DecisionType.SELECT_MOVE_DESTINATION
    state.decision_context.selected_source = action.clearing_id


def apply_move_destination(state: GameState, action: SelectMoveDestination) -> None:
    source = state.decision_context.selected_source
    if source is None:
        raise ValueError("No selected source for move")
    if state.board.warriors[source][Faction.ALLIANCE] <= 0:
        raise ValueError("No Alliance warrior at source")
    state.board.warriors[source][Faction.ALLIANCE] -= 1
    state.board.warriors[action.clearing_id][Faction.ALLIANCE] += 1
    state.decision_context.decision_type = DecisionType.MAIN_ACTION
    state.decision_context.selected_source = None
    _use_military_operation(state)


def apply_battle_select_clearing(state: GameState, action: SelectBattleClearing) -> None:
    state.decision_context.decision_type = DecisionType.SELECT_BATTLE_TARGET
    state.decision_context.selected_battle_clearing = action.clearing_id


def apply_battle_select_target(state: GameState, action: SelectBattleTarget) -> None:
    clearing = state.decision_context.selected_battle_clearing
    if clearing is None:
        raise ValueError("No battle clearing selected")
    target = Faction(action.target_faction)
    resolve_basic_battle(state, Faction.ALLIANCE, target, clearing)
    state.decision_context.decision_type = DecisionType.MAIN_ACTION
    state.decision_context.selected_battle_clearing = None
    _use_military_operation(state)


def apply_recruit(state: GameState, action: Recruit) -> None:
    if state.turn.phase != Phase.EVENING:
        raise ValueError("Alliance recruit can only be taken in Evening")
    if action.clearing_id not in _legal_evening_recruit_clearings(state):
        raise ValueError("Can only recruit in a clearing with a base")
    if _alliance_warriors_in_supply(state) <= 0:
        raise ValueError("No Alliance warriors in supply")
    state.board.warriors[action.clearing_id][Faction.ALLIANCE] += 1
    _use_military_operation(state)


def apply_organize(state: GameState, action: Organize) -> None:
    if state.turn.phase != Phase.EVENING:
        raise ValueError("Organize can only be taken in Evening")
    if action.clearing_id not in _legal_organize_clearings(state):
        raise ValueError("Organize requires an Alliance warrior in an unsympathetic clearing")
    state.board.warriors[action.clearing_id][Faction.ALLIANCE] -= 1
    state.board.tokens[action.clearing_id][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    state.alliance.sympathy_in_supply -= 1
    state.scores[Faction.ALLIANCE] += _sympathy_vp_reward(state)
    _use_military_operation(state)


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


def trigger_outrage(
    state: GameState,
    offending_faction: Faction,
    clearing_id: int,
    require_sympathy_present: bool = True,
) -> None:
    """Resolve Alliance outrage caused by another faction in a sympathetic clearing."""

    if offending_faction == Faction.ALLIANCE:
        return
    if require_sympathy_present and TokenType.SYMPATHY not in state.board.tokens[clearing_id][Faction.ALLIANCE]:
        return
    hand = _faction_hand(state, offending_faction)
    if hand is None:
        return
    clearing_suit = state.board.clearings[clearing_id].suit
    matching_card_id = next(
        (
            card_id
            for card_id in hand
            if state.cards[card_id].suit in (clearing_suit, Suit.BIRD)
        ),
        None,
    )
    if matching_card_id is not None:
        hand.remove(matching_card_id)
        gain_supporter(state, matching_card_id)
        return
    if state.draw_pile:
        gain_supporter(state, state.draw_pile.pop())


def can_gain_supporter(state: GameState) -> bool:
    """Supporters are capped at 5 when the Alliance has no bases."""

    has_any_base = any(state.alliance.bases.values())
    if has_any_base:
        return True
    return len(state.alliance.supporters) < 5


def _faction_hand(state: GameState, faction: Faction) -> list[int] | None:
    if faction == Faction.MARQUISE:
        return state.marquise.hand
    if faction == Faction.EYRIE:
        return state.eyrie.hand
    if faction == Faction.ALLIANCE:
        return state.alliance.hand
    if faction == Faction.VAGABOND:
        return state.vagabond.hand
    return None


def legal_crafting_cards(state: GameState) -> list[int]:
    """Alliance crafts by activating sympathy tokens in Daylight."""

    return legal_craft_cards(state, state.alliance.hand, Faction.ALLIANCE)


def _legal_train_cards(state: GameState) -> list[int]:
    built_base_suits = {suit for suit, built in state.alliance.bases.items() if built}
    if not built_base_suits or _alliance_warriors_in_supply(state) <= 0:
        return []
    return [
        card_id
        for card_id in state.alliance.hand
        if state.cards[card_id].suit in built_base_suits or state.cards[card_id].suit == Suit.BIRD
    ]


def _legal_evening_recruit_clearings(state: GameState) -> list[int]:
    if state.turn.phase != Phase.EVENING or _alliance_warriors_in_supply(state) <= 0:
        return []
    return [
        cid
        for cid, buildings in state.board.buildings.items()
        if any(building == BuildingType.BASE for building in buildings[Faction.ALLIANCE])
    ]


def _legal_organize_clearings(state: GameState) -> list[int]:
    if state.turn.phase != Phase.EVENING or state.alliance.sympathy_in_supply <= 0:
        return []
    return [
        cid
        for cid in state.board.clearings
        if state.board.warriors[cid][Faction.ALLIANCE] > 0
        and TokenType.SYMPATHY not in state.board.tokens[cid][Faction.ALLIANCE]
    ]


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


def _use_military_operation(state: GameState) -> None:
    if state.turn.phase != Phase.EVENING:
        raise ValueError("Military operations can only be used in Evening")
    if state.alliance.military_ops_used >= state.alliance.officers:
        raise ValueError("No military operations remaining")
    state.alliance.military_ops_used += 1
    state.alliance.crafting_window_open = False


def _resolve_favor(state: GameState, favor_suit: Suit) -> None:
    for cid, clearing in state.board.clearings.items():
        if clearing.suit != favor_suit:
            continue
        state.board.warriors[cid][Faction.MARQUISE] = 0
        state.board.warriors[cid][Faction.EYRIE] = 0
        state.board.buildings[cid][Faction.MARQUISE].clear()
        state.board.buildings[cid][Faction.EYRIE].clear()
        state.board.tokens[cid][Faction.MARQUISE] = [
            token for token in state.board.tokens[cid][Faction.MARQUISE] if token != TokenType.WOOD
        ]
