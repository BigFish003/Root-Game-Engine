"""Eyrie-specific legal action generation and application."""

from __future__ import annotations

from ..actions import (
    AddToDecree,
    Build,
    Craft,
    EndPhase,
    FallIntoTurmoil,
    Recruit,
    SelectEyrieLeader,
    SelectBattleClearing,
    SelectBattleTarget,
    SelectMoveDestination,
    SelectMoveSource,
)
from ..enums import BuildingType, CardTag, DecisionType, Faction, Phase, Suit, TokenType
from ..models import GameState
from . import alliance as alliance_rules
from .combat import legal_battle_clearings, legal_battle_targets, resolve_basic_battle
from .crafting import legal_craft_cards
from .movement import legal_move_destinations, legal_move_sources


def valid_actions(state: GameState) -> list:
    if state.eyrie.pending_leader_selection:
        return [SelectEyrieLeader(leader) for leader in _available_leaders(state)]
    if state.turn.phase == Phase.BIRDSONG:
        actions: list = []
        if state.eyrie.birdsong_cards_added < 2:
            for card_id in state.eyrie.hand:
                for column in ["recruit", "move", "battle", "build"]:
                    actions.append(AddToDecree(card_id=card_id, column=column))
        if state.eyrie.birdsong_cards_added >= 1 or not state.eyrie.hand:
            actions.append(EndPhase())
        return actions
    if state.turn.phase != Phase.DAYLIGHT:
        return [EndPhase()]

    ctx = state.decision_context
    if ctx.decision_type == DecisionType.MAIN_ACTION:
        _ensure_decree_progress_initialized(state)
        actions: list = []
        if state.eyrie.crafting_window_open:
            actions.extend(Craft(card_id) for card_id in legal_craft_cards(state, state.eyrie.hand, Faction.EYRIE))

        decree_actions = _current_decree_actions(state)
        if decree_actions:
            actions.extend(decree_actions)
        elif _has_remaining_decree_cards(state):
            actions.append(FallIntoTurmoil())
        else:
            actions.append(EndPhase())
        return actions
    if ctx.decision_type == DecisionType.SELECT_MOVE_DESTINATION and ctx.selected_source is not None:
        warriors_at_source = state.board.warriors[ctx.selected_source][Faction.EYRIE]
        actions = [
            SelectMoveDestination(clearing_id=cid, warriors=warriors_to_move)
            for cid in legal_move_destinations(state, Faction.EYRIE, ctx.selected_source)
            for warriors_to_move in range(1, warriors_at_source + 1)
        ]
        return actions
    if ctx.decision_type == DecisionType.SELECT_BATTLE_TARGET and ctx.selected_battle_clearing is not None:
        return [
            SelectBattleTarget(f.value)
            for f in legal_battle_targets(state, Faction.EYRIE, ctx.selected_battle_clearing)
        ]
    return []


def apply_recruit(state: GameState, action: Recruit) -> None:
    if state.eyrie.leader == "charismatic":
        warriors_to_place = 2
    else:
        warriors_to_place = 1
    if action.clearing_id == state.marquise.keep_clearing:
        raise ValueError("Only the Marquise can place pieces in the keep clearing")
    if state.eyrie.warriors_in_supply <= 0:
        raise ValueError("No Eyrie warriors in supply")
    warriors_to_place = min(warriors_to_place, state.eyrie.warriors_in_supply)
    state.board.warriors[action.clearing_id][Faction.EYRIE] += warriors_to_place
    state.eyrie.warriors_in_supply -= warriors_to_place
    _consume_decree_card(state, "recruit", state.board.clearings[action.clearing_id].suit)


def apply_build(state: GameState, action: Build) -> None:
    if action.clearing_id == state.marquise.keep_clearing:
        raise ValueError("Only the Marquise can place pieces in the keep clearing")
    if action.building_type != BuildingType.ROOST:
        raise ValueError("Eyrie can only build roosts")
    if state.eyrie.roosts_in_supply <= 0:
        raise ValueError("No roosts left")
    if BuildingType.ROOST in state.board.buildings[action.clearing_id][Faction.EYRIE]:
        raise ValueError("Clearing already has a roost")
    if len(state.board.buildings[action.clearing_id][Faction.EYRIE]) >= state.board.clearings[action.clearing_id].building_slots:
        raise ValueError("No free slot")
    state.board.buildings[action.clearing_id][Faction.EYRIE].append(BuildingType.ROOST)
    state.eyrie.roosts_in_supply -= 1
    _consume_decree_card(state, "build", state.board.clearings[action.clearing_id].suit)


def apply_move_source(state: GameState, action: SelectMoveSource) -> None:
    state.decision_context.decision_type = DecisionType.SELECT_MOVE_DESTINATION
    state.decision_context.selected_source = action.clearing_id


def apply_move_destination(state: GameState, action: SelectMoveDestination) -> None:
    source = state.decision_context.selected_source
    if source is None:
        raise ValueError("No source selected")
    available_warriors = state.board.warriors[source][Faction.EYRIE]
    if available_warriors <= 0:
        raise ValueError("No Eyrie warrior at source")
    if action.warriors <= 0:
        raise ValueError("Must move at least one Eyrie warrior")
    if action.warriors > available_warriors:
        raise ValueError("Cannot move more Eyrie warriors than are present")
    state.board.warriors[source][Faction.EYRIE] -= action.warriors
    state.board.warriors[action.clearing_id][Faction.EYRIE] += action.warriors
    alliance_rules.trigger_outrage(state, Faction.EYRIE, action.clearing_id)
    state.decision_context.decision_type = DecisionType.MAIN_ACTION
    _consume_decree_card(state, "move", state.board.clearings[source].suit)
    state.decision_context.selected_source = None


def apply_battle_select_clearing(state: GameState, action: SelectBattleClearing) -> None:
    state.decision_context.decision_type = DecisionType.SELECT_BATTLE_TARGET
    state.decision_context.selected_battle_clearing = action.clearing_id


def apply_battle_select_target(state: GameState, action: SelectBattleTarget) -> None:
    clearing = state.decision_context.selected_battle_clearing
    if clearing is None:
        raise ValueError("No battle clearing selected")
    target = Faction(action.target_faction)
    resolve_basic_battle(
        state,
        Faction.EYRIE,
        target,
        clearing,
        attacker_extra_hits=1 if state.eyrie.leader == "commander" else 0,
        despot_bonus=state.eyrie.leader == "despot",
    )
    _consume_decree_card(state, "battle", state.board.clearings[clearing].suit)
    state.decision_context.decision_type = DecisionType.MAIN_ACTION
    state.decision_context.selected_battle_clearing = None


def apply_craft(state: GameState, action: Craft) -> None:
    if action.card_id not in legal_craft_cards(state, state.eyrie.hand, Faction.EYRIE):
        raise ValueError("Card cannot be crafted with available roosts")
    if action.card_id not in state.eyrie.hand:
        raise ValueError("Card not in hand")
    if not state.eyrie.crafting_window_open:
        raise ValueError("Crafting is only available before decree resolution")
    card = state.cards[action.card_id]
    state.eyrie.hand.remove(action.card_id)
    if CardTag.ITEM in card.tags:
        state.scores[Faction.EYRIE] += 1
    elif card.vp_on_craft > 0:
        state.scores[Faction.EYRIE] += card.vp_on_craft
    if card.name.startswith("Favor of the"):
        _resolve_favor(state, card.suit)
    if CardTag.PERSISTENT_EFFECT in card.tags:
        state.eyrie.crafted_effects.append(card.name)
    else:
        state.discard_pile.append(action.card_id)


def apply_add_to_decree(state: GameState, action: AddToDecree) -> None:
    if action.card_id not in state.eyrie.hand:
        raise ValueError("Card not in hand")
    if action.column not in state.eyrie.decree:
        raise ValueError("Invalid decree column")
    if state.eyrie.birdsong_cards_added >= 2:
        raise ValueError("Eyrie can add at most 2 cards to decree in birdsong")
    state.eyrie.hand.remove(action.card_id)
    state.eyrie.decree[action.column].append(action.card_id)
    state.eyrie.birdsong_cards_added += 1


def apply_fall_into_turmoil(state: GameState, action: FallIntoTurmoil) -> None:
    del action
    if state.eyrie.leader not in state.eyrie.turmoiled_leaders:
        state.eyrie.turmoiled_leaders.append(state.eyrie.leader)
    bird_cards_in_decree = sum(
        1
        for cards in state.eyrie.decree.values()
        for card_id in cards
        if _card_suit(state, card_id) == Suit.BIRD
    )
    state.scores[Faction.EYRIE] = max(0, state.scores[Faction.EYRIE] - bird_cards_in_decree)
    for cards in state.eyrie.decree.values():
        state.discard_pile.extend(card_id for card_id in cards if card_id > 0)
        cards.clear()
    state.eyrie.decree_cards_remaining = {key: [] for key in state.eyrie.decree}
    state.eyrie.crafting_window_open = False
    state.eyrie.resolving_decree = False
    state.eyrie.decree_column_index = 0
    state.eyrie.pending_leader_selection = True


def apply_select_leader(state: GameState, action: SelectEyrieLeader) -> None:
    available = _available_leaders(state)
    if action.leader not in available:
        raise ValueError("Leader is not available to turmoil into")
    state.eyrie.leader = action.leader
    _assign_leader_viziers(state, action.leader)
    state.eyrie.pending_leader_selection = False
    state.turn.phase = Phase.EVENING
    state.decision_context.decision_type = DecisionType.MAIN_ACTION


def _legal_recruit_clearings(state: GameState) -> list[int]:
    if state.eyrie.warriors_in_supply <= 0:
        return []
    return [
        cid
        for cid, buildings in state.board.buildings.items()
        if cid != state.marquise.keep_clearing
        and any(b == BuildingType.ROOST for b in buildings[Faction.EYRIE])
    ]


def _legal_roost_builds(state: GameState) -> list[int]:
    result: list[int] = []
    for cid in state.board.clearings:
        if state.board.warriors[cid][Faction.EYRIE] <= 0:
            continue
        existing = state.board.buildings[cid][Faction.EYRIE]
        if BuildingType.ROOST in existing:
            continue
        slots = state.board.clearings[cid].building_slots
        if len(existing) < slots:
            result.append(cid)
    return result


def _current_decree_actions(state: GameState) -> list:
    _advance_decree_column(state)
    column = _current_column(state)
    if column is None:
        return []
    remaining = state.eyrie.decree_cards_remaining[column]
    if not remaining:
        return []
    suits = [_card_suit(state, card_id) for card_id in remaining]

    if column == "recruit":
        return [Recruit(cid) for cid in _legal_recruit_clearings(state) if _suit_matches_any(state, cid, suits)]
    if column == "move":
        return [SelectMoveSource(cid) for cid in legal_move_sources(state, Faction.EYRIE) if _suit_matches_any(state, cid, suits)]
    if column == "battle":
        return [SelectBattleClearing(cid) for cid in legal_battle_clearings(state, Faction.EYRIE) if _suit_matches_any(state, cid, suits)]
    return [
        Build(clearing_id=cid, building_type=BuildingType.ROOST)
        for cid in _legal_roost_builds(state)
        if _suit_matches_any(state, cid, suits)
    ]


def _card_suit(state: GameState, card_id: int) -> Suit:
    if card_id < 0:
        return Suit.BIRD
    return state.cards[card_id].suit


def roost_points_for_evening(state: GameState) -> int:
    return 7 - state.eyrie.roosts_in_supply


def roost_draw_bonus(state: GameState) -> int:
    roosts_built = 7 - state.eyrie.roosts_in_supply
    bonus = 0
    if roosts_built >= 3:
        bonus += 1
    if roosts_built >= 6:
        bonus += 1
    return bonus


def _suit_matches_any(state: GameState, clearing_id: int, suits: list[Suit]) -> bool:
    clearing_suit = state.board.clearings[clearing_id].suit
    return any(s == Suit.BIRD or s == clearing_suit for s in suits)


def _consume_decree_card(state: GameState, column: str, clearing_suit: Suit) -> None:
    _ensure_decree_progress_initialized(state)
    if state.eyrie.crafting_window_open:
        state.eyrie.crafting_window_open = False
    remaining = state.eyrie.decree_cards_remaining[column]
    for idx, card_id in enumerate(remaining):
        suit = _card_suit(state, card_id)
        if suit == clearing_suit:
            remaining.pop(idx)
            _advance_decree_column(state)
            return
    for idx, card_id in enumerate(remaining):
        if _card_suit(state, card_id) == Suit.BIRD:
            remaining.pop(idx)
            _advance_decree_column(state)
            return
    raise ValueError("Action does not satisfy any decree card in current column")


def _advance_decree_column(state: GameState) -> None:
    columns = ["recruit", "move", "battle", "build"]
    while state.eyrie.decree_column_index < len(columns):
        if state.eyrie.decree_cards_remaining[columns[state.eyrie.decree_column_index]]:
            return
        state.eyrie.decree_column_index += 1


def _current_column(state: GameState) -> str | None:
    columns = ["recruit", "move", "battle", "build"]
    if state.eyrie.decree_column_index >= len(columns):
        return None
    return columns[state.eyrie.decree_column_index]


def _has_remaining_decree_cards(state: GameState) -> bool:
    return any(state.eyrie.decree_cards_remaining[c] for c in ["recruit", "move", "battle", "build"])


def _ensure_decree_progress_initialized(state: GameState) -> None:
    if state.eyrie.resolving_decree:
        return
    if state.eyrie.decree_cards_remaining == {key: [] for key in state.eyrie.decree} and any(
        state.eyrie.decree.values()
    ):
        state.eyrie.decree_cards_remaining = {
            key: list(cards) for key, cards in state.eyrie.decree.items()
        }
    state.eyrie.resolving_decree = True


def _resolve_favor(state: GameState, favor_suit: Suit) -> None:
    for cid, clearing in state.board.clearings.items():
        if clearing.suit != favor_suit:
            continue
        state.board.warriors[cid][Faction.MARQUISE] = 0
        state.board.warriors[cid][Faction.ALLIANCE] = 0
        removed = len(state.board.buildings[cid][Faction.MARQUISE]) + len(state.board.buildings[cid][Faction.ALLIANCE])
        state.board.buildings[cid][Faction.MARQUISE].clear()
        state.board.buildings[cid][Faction.ALLIANCE].clear()
        removed += sum(1 for token in state.board.tokens[cid][Faction.MARQUISE] if token == TokenType.KEEP)
        state.board.tokens[cid][Faction.MARQUISE] = [
            token for token in state.board.tokens[cid][Faction.MARQUISE] if token != TokenType.KEEP
        ]
        sympathy_removed = sum(
            1 for token in state.board.tokens[cid][Faction.ALLIANCE] if token == TokenType.SYMPATHY
        )
        removed += sympathy_removed
        state.board.tokens[cid][Faction.ALLIANCE] = [
            token for token in state.board.tokens[cid][Faction.ALLIANCE] if token != TokenType.SYMPATHY
        ]
        state.scores[Faction.EYRIE] += removed
        for _ in range(sympathy_removed):
            alliance_rules.trigger_outrage(state, Faction.EYRIE, cid, require_sympathy_present=False)


def _assign_leader_viziers(state: GameState, leader: str) -> None:
    vizier_card_ids = {"recruit": -101, "move": -102, "battle": -103, "build": -104}
    mapping = {
        "despot": ("move", "build"),
        "commander": ("move", "battle"),
        "charismatic": ("recruit", "battle"),
        "builder": ("recruit", "move"),
    }
    for cards in state.eyrie.decree.values():
        cards[:] = [card_id for card_id in cards if card_id > 0]
    for column in mapping[leader]:
        state.eyrie.decree[column].append(vizier_card_ids[column])


def _available_leaders(state: GameState) -> list[str]:
    all_leaders = ["despot", "commander", "charismatic", "builder"]
    if len(state.eyrie.turmoiled_leaders) >= len(all_leaders):
        state.eyrie.turmoiled_leaders.clear()
    return [leader for leader in all_leaders if leader not in state.eyrie.turmoiled_leaders]
