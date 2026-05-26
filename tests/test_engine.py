from __future__ import annotations

import pytest

from root_engine.actions import (
    AddToDecree,
    Build,
    Craft,
    EndPhase,
    FallIntoTurmoil,
    Mobilize,
    Organize,
    Recruit,
    Revolt,
    SelectEyrieLeader,
    SelectMoveDestination,
    SelectMoveSource,
    SpreadSympathy,
    Train,
)
from root_engine.engine import RootEngine
from root_engine.enums import BuildingType, DecisionType, Faction, Phase, Suit, TokenType
from root_engine.rules import alliance as alliance_rules
from root_engine.rules import combat as combat_rules
from root_engine.rules import eyrie as eyrie_rules
from root_engine.rules import marquise as marquise_rules


def _advance_to_alliance_birdsong(engine: RootEngine) -> None:
    while engine.get_state().turn.current_faction != Faction.ALLIANCE:
        actions = engine.get_valid_actions()
        end_phase = next((a for a in actions if isinstance(a, EndPhase)), None)
        engine.apply_action(end_phase if end_phase is not None else actions[0])


def test_reset_initial_state_has_expected_markers() -> None:
    engine = RootEngine(seed=7)
    state = engine.get_state()

    assert state.turn.current_faction == Faction.MARQUISE
    assert state.turn.phase == Phase.BIRDSONG
    assert state.marquise.keep_clearing == 1
    assert state.board.warriors[12][Faction.EYRIE] == 6
    assert len(state.alliance.supporters) == 3
    assert len(state.alliance.hand) == 0


def test_valid_actions_non_empty_for_start_state() -> None:
    engine = RootEngine(seed=1)
    actions = engine.get_valid_actions()

    assert actions == [EndPhase()]


def test_illegal_action_raises() -> None:
    engine = RootEngine(seed=2)

    with pytest.raises(ValueError):
        engine.apply_action(Recruit(clearing_id=12))


def test_recruit_and_build_mutate_state() -> None:
    engine = RootEngine(seed=3)
    engine.apply_action(EndPhase())

    recruit = next(a for a in engine.get_valid_actions() if isinstance(a, Recruit))
    before_supply = engine.get_state().marquise.warriors_in_supply
    engine.apply_action(recruit)
    assert engine.get_state().marquise.warriors_in_supply == before_supply - 1

    build = next(
        a
        for a in engine.get_valid_actions()
        if isinstance(a, Build) and a.building_type == BuildingType.SAWMILL
    )
    before_score = engine.get_state().scores[Faction.MARQUISE]
    engine.apply_action(build)
    assert engine.get_state().scores[Faction.MARQUISE] == before_score + 1


def test_marquise_build_scoring_track_and_recruiter_draw_bonus() -> None:
    engine = RootEngine(seed=203, excluded_factions={Faction.EYRIE, Faction.ALLIANCE, Faction.VAGABOND})
    state = engine.get_state()
    state.board.buildings[2][Faction.MARQUISE] = [BuildingType.RECRUITER]
    state.marquise.buildings_in_supply[BuildingType.RECRUITER] = 5
    state.board.warriors[2][Faction.MARQUISE] = 5
    state.board.tokens[2][Faction.MARQUISE] = [TokenType.WOOD, TokenType.WOOD, TokenType.WOOD, TokenType.WOOD]
    state.scores[Faction.MARQUISE] = 0

    engine.apply_action(EndPhase())  # birdsong -> daylight

    first_build = next(
        action
        for action in engine.get_valid_actions()
        if isinstance(action, Build) and action.clearing_id == 2 and action.building_type == BuildingType.RECRUITER
    )
    engine.apply_action(first_build)
    assert state.scores[Faction.MARQUISE] == 1

    state.marquise.daylight_actions_used = 0
    second_build = next(
        action
        for action in engine.get_valid_actions()
        if isinstance(action, Build) and action.building_type == BuildingType.RECRUITER
    )
    engine.apply_action(second_build)
    assert state.scores[Faction.MARQUISE] == 3

    hand_before_evening = len(state.marquise.hand)
    engine.apply_action(EndPhase())  # daylight -> evening
    engine.apply_action(EndPhase())  # evening resolution
    assert len(state.marquise.hand) == hand_before_evening + 2


def test_atomic_move_selection_changes_context_and_board() -> None:
    engine = RootEngine(seed=4)
    engine.apply_action(EndPhase())

    select_source = next(a for a in engine.get_valid_actions() if isinstance(a, SelectMoveSource))
    src1 = select_source.clearing_id
    src1_before = engine.get_state().board.warriors[src1][Faction.MARQUISE]
    actions_before = engine.get_state().marquise.daylight_actions_used
    engine.apply_action(select_source)

    assert engine.get_state().decision_context.decision_type == DecisionType.SELECT_MOVE_DESTINATION
    first_dest_action = next(a for a in engine.get_valid_actions() if isinstance(a, SelectMoveDestination))
    dest1 = first_dest_action.clearing_id
    dest1_before = engine.get_state().board.warriors[dest1][Faction.MARQUISE]

    engine.apply_action(first_dest_action)
    assert engine.get_state().board.warriors[src1][Faction.MARQUISE] == src1_before - 1
    assert engine.get_state().board.warriors[dest1][Faction.MARQUISE] == dest1_before + 1
    assert engine.get_state().marquise.daylight_actions_used == actions_before

    second_source = next(a for a in engine.get_valid_actions() if isinstance(a, SelectMoveSource))
    src2 = second_source.clearing_id
    src2_before = engine.get_state().board.warriors[src2][Faction.MARQUISE]
    engine.apply_action(second_source)
    second_dest_action = next(a for a in engine.get_valid_actions() if isinstance(a, SelectMoveDestination))
    dest2 = second_dest_action.clearing_id
    dest2_before = engine.get_state().board.warriors[dest2][Faction.MARQUISE]
    engine.apply_action(second_dest_action)

    assert engine.get_state().board.warriors[src2][Faction.MARQUISE] == src2_before - 1
    assert engine.get_state().board.warriors[dest2][Faction.MARQUISE] == dest2_before + 1
    assert engine.get_state().marquise.daylight_actions_used == actions_before + 1
    assert engine.get_state().decision_context.decision_type == DecisionType.MAIN_ACTION


def test_turn_progression_via_end_phase() -> None:
    engine = RootEngine(seed=5)

    engine.apply_action(EndPhase())
    assert engine.get_state().turn.phase == Phase.DAYLIGHT
    engine.apply_action(EndPhase())
    assert engine.get_state().turn.phase == Phase.EVENING
    engine.apply_action(EndPhase())
    assert engine.get_state().turn.current_faction == Faction.EYRIE
    assert engine.get_state().turn.phase == Phase.BIRDSONG


def test_can_exclude_a_faction_for_three_player_turn_order() -> None:
    engine = RootEngine(seed=6, excluded_factions={Faction.VAGABOND})
    state = engine.get_state()

    assert state.turn.turn_order == [Faction.MARQUISE, Faction.EYRIE, Faction.ALLIANCE]
    assert state.vagabond.location is None
    assert state.vagabond.hand == []

    for _ in range(20):
        actions = engine.get_valid_actions()
        end_phase = next((a for a in actions if isinstance(a, EndPhase)), None)
        engine.apply_action(end_phase if end_phase is not None else actions[0])
        if (
            engine.get_state().turn.current_faction == Faction.MARQUISE
            and engine.get_state().turn.round_number == 2
        ):
            break
    assert engine.get_state().turn.current_faction == Faction.MARQUISE


def test_deterministic_seed() -> None:
    e1 = RootEngine(seed=42)
    e2 = RootEngine(seed=42)

    assert e1.get_state().draw_pile == e2.get_state().draw_pile


def test_clone_is_independent() -> None:
    engine = RootEngine(seed=11)
    clone = engine.clone()
    clone.apply_action(EndPhase())

    recruit = next(a for a in clone.get_valid_actions() if isinstance(a, Recruit))
    clone.apply_action(recruit)

    assert clone.get_state().marquise.warriors_in_supply != engine.get_state().marquise.warriors_in_supply


def test_marquise_birdsong_places_wood_at_sawmills() -> None:
    engine = RootEngine(seed=13)
    before_wood = sum(
        1
        for token in engine.get_state().board.tokens[1][Faction.MARQUISE]
        if token.value == "wood"
    )
    engine.apply_action(EndPhase())
    after_wood = sum(
        1
        for token in engine.get_state().board.tokens[1][Faction.MARQUISE]
        if token.value == "wood"
    )
    assert after_wood == before_wood + 1


def test_marquise_recruit_is_once_per_turn() -> None:
    engine = RootEngine(seed=17)
    engine.apply_action(EndPhase())
    recruit = next(a for a in engine.get_valid_actions() if isinstance(a, Recruit))
    engine.apply_action(recruit)
    assert not any(isinstance(a, Recruit) for a in engine.get_valid_actions())


def test_base_deck_contains_expected_card_count() -> None:
    engine = RootEngine(seed=21)
    assert len(engine.get_state().cards) == 53


def test_marquise_can_craft_multiple_cards_with_workshop_budget() -> None:
    engine = RootEngine(seed=23)
    state = engine.get_state()
    state.board.buildings[1][Faction.MARQUISE].append(BuildingType.WORKSHOP)  # fox
    state.board.buildings[3][Faction.MARQUISE].append(BuildingType.WORKSHOP)  # mouse
    state.board.buildings[5][Faction.MARQUISE].append(BuildingType.WORKSHOP)  # rabbit

    tax_collector = next(
        cid
        for cid, card in state.cards.items()
        if card.name == "Tax Collector" and card.suit.value == "fox"
    )
    visit_friends = next(
        cid
        for cid, card in state.cards.items()
        if card.name == "A Visit to Friends" and card.suit.value == "rabbit"
    )
    state.marquise.hand = [tax_collector, visit_friends]

    engine.apply_action(EndPhase())  # birdsong -> daylight, initializes crafting power

    first_craft = next(
        action
        for action in engine.get_valid_actions()
        if isinstance(action, Craft) and action.card_id == tax_collector
    )
    engine.apply_action(first_craft)
    assert state.marquise.crafting_power == {
        Suit.FOX: 0,
        Suit.RABBIT: 1,
        Suit.MOUSE: 0,
    }

    second_craft = next(
        action
        for action in engine.get_valid_actions()
        if isinstance(action, Craft) and action.card_id == visit_friends
    )
    engine.apply_action(second_craft)
    assert not any(isinstance(action, Craft) for action in engine.get_valid_actions())


def test_marquise_crafting_only_offered_before_non_craft_daylight_action() -> None:
    engine = RootEngine(seed=29)
    state = engine.get_state()
    state.board.buildings[1][Faction.MARQUISE].append(BuildingType.WORKSHOP)  # fox workshop
    anvil = next(cid for cid, card in state.cards.items() if card.name == "Anvil")
    state.marquise.hand = [anvil]

    engine.apply_action(EndPhase())  # birdsong -> daylight
    assert any(isinstance(action, Craft) for action in engine.get_valid_actions())

    recruit = next(action for action in engine.get_valid_actions() if isinstance(action, Recruit))
    engine.apply_action(recruit)
    assert not any(isinstance(action, Craft) for action in engine.get_valid_actions())


def test_eyrie_birdsong_can_add_cards_to_decree() -> None:
    engine = RootEngine(seed=31)
    while engine.get_state().turn.current_faction != Faction.EYRIE:
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())

    state = engine.get_state()
    assert not any(isinstance(action, EndPhase) for action in engine.get_valid_actions())
    card_id = state.eyrie.hand[0]
    add = next(
        action
        for action in engine.get_valid_actions()
        if isinstance(action, AddToDecree) and action.card_id == card_id and action.column == "recruit"
    )
    engine.apply_action(add)
    assert card_id in state.eyrie.decree["recruit"]
    assert card_id not in state.eyrie.hand
    assert any(isinstance(action, EndPhase) for action in engine.get_valid_actions())


def test_eyrie_daylight_craft_before_resolving_decree() -> None:
    engine = RootEngine(seed=37)
    while engine.get_state().turn.current_faction != Faction.EYRIE:
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
    state = engine.get_state()

    anvil = next(cid for cid, card in state.cards.items() if card.name == "Anvil")
    state.eyrie.hand = [anvil]
    state.eyrie.decree["recruit"] = [anvil]
    state.board.buildings[6][Faction.EYRIE].append(BuildingType.ROOST)  # fox roost for crafting

    state.eyrie.birdsong_cards_added = 1
    engine.apply_action(EndPhase())  # birdsong -> daylight
    assert any(isinstance(action, Craft) for action in engine.get_valid_actions())
    engine.apply_action(Craft(card_id=anvil))
    assert state.scores[Faction.EYRIE] == 1
    recruit = next(action for action in engine.get_valid_actions() if isinstance(action, Recruit))
    engine.apply_action(recruit)
    assert not state.eyrie.crafting_window_open


def test_eyrie_roost_scores_in_evening_based_on_total_roosts_and_gets_draw_bonus() -> None:
    engine = RootEngine(seed=305, excluded_factions={Faction.MARQUISE, Faction.ALLIANCE, Faction.VAGABOND})
    while engine.get_state().turn.current_faction != Faction.EYRIE:
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
    state = engine.get_state()
    state.eyrie.decree = {"recruit": [], "move": [], "battle": [], "build": [-104]}
    state.eyrie.decree_cards_remaining = {"recruit": [], "move": [], "battle": [], "build": [-104]}
    state.eyrie.birdsong_cards_added = 1
    state.board.warriors[11][Faction.EYRIE] = 2
    state.board.buildings[12][Faction.EYRIE] = [BuildingType.ROOST]
    state.eyrie.roosts_in_supply = 6
    state.scores[Faction.EYRIE] = 0

    engine.apply_action(EndPhase())  # birdsong -> daylight
    build = next(action for action in engine.get_valid_actions() if isinstance(action, Build))
    engine.apply_action(build)
    assert state.scores[Faction.EYRIE] == 0

    state.eyrie.roosts_in_supply = 2  # simulate five roosts already on map
    state.board.buildings[12][Faction.EYRIE] = [BuildingType.ROOST] * 5
    state.eyrie.decree = {"recruit": [], "move": [], "battle": [], "build": []}
    state.eyrie.decree_cards_remaining = {"recruit": [], "move": [], "battle": [], "build": []}
    hand_before_evening = len(state.eyrie.hand)
    engine.apply_action(EndPhase())  # daylight -> evening
    engine.apply_action(EndPhase())  # evening resolution
    assert state.scores[Faction.EYRIE] == 5
    assert len(state.eyrie.hand) == hand_before_evening + 2


def test_eyrie_move_decree_allows_moving_multiple_warriors() -> None:
    engine = RootEngine(seed=39)
    while engine.get_state().turn.current_faction != Faction.EYRIE:
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
    state = engine.get_state()

    state.eyrie.decree = {"recruit": [], "move": [-102], "battle": [], "build": []}
    state.eyrie.decree_cards_remaining = {"recruit": [], "move": [-102], "battle": [], "build": []}
    state.eyrie.birdsong_cards_added = 1
    state.board.warriors[12][Faction.EYRIE] = 6

    engine.apply_action(EndPhase())  # birdsong -> daylight
    source_action = next(
        action
        for action in engine.get_valid_actions()
        if isinstance(action, SelectMoveSource) and action.clearing_id == 12
    )
    engine.apply_action(source_action)

    destination_actions = [
        action for action in engine.get_valid_actions() if isinstance(action, SelectMoveDestination)
    ]
    assert any(action.warriors == 6 for action in destination_actions)
    move_all_action = next(action for action in destination_actions if action.warriors == 6)
    destination = move_all_action.clearing_id
    before_destination = state.board.warriors[destination][Faction.EYRIE]

    engine.apply_action(move_all_action)

    assert state.board.warriors[12][Faction.EYRIE] == 0
    assert state.board.warriors[destination][Faction.EYRIE] == before_destination + 6


def test_eyrie_resolves_decree_in_column_order_and_turmoils_if_stuck() -> None:
    engine = RootEngine(seed=41)
    while engine.get_state().turn.current_faction != Faction.EYRIE:
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
    state = engine.get_state()

    fox_card = next(cid for cid, card in state.cards.items() if card.suit == Suit.FOX)
    mouse_card = next(cid for cid, card in state.cards.items() if card.suit == Suit.MOUSE and cid != fox_card)
    state.eyrie.decree = {"recruit": [fox_card], "move": [mouse_card], "battle": [], "build": []}
    state.eyrie.decree_cards_remaining = {"recruit": [fox_card], "move": [mouse_card], "battle": [], "build": []}
    state.board.buildings[6][Faction.EYRIE].append(BuildingType.ROOST)  # fox clearing
    state.board.warriors[12][Faction.EYRIE] = 0
    state.eyrie.warriors_in_supply += 6

    state.eyrie.birdsong_cards_added = 1
    engine.apply_action(EndPhase())  # birdsong -> daylight
    recruit = next(action for action in engine.get_valid_actions() if isinstance(action, Recruit))
    engine.apply_action(recruit)
    actions = engine.get_valid_actions()
    assert not any(isinstance(action, Recruit) for action in actions)
    assert any(isinstance(action, FallIntoTurmoil) for action in actions)


def test_eyrie_turmoil_causes_bird_card_point_loss_and_moves_to_evening() -> None:
    engine = RootEngine(seed=42)
    while engine.get_state().turn.current_faction != Faction.EYRIE:
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
    state = engine.get_state()

    bird_card = next(cid for cid, card in state.cards.items() if card.suit == Suit.BIRD)
    clearing_suit = state.board.clearings[6].suit
    off_suit_card = next(
        cid for cid, card in state.cards.items() if card.suit not in (Suit.BIRD, clearing_suit)
    )
    state.eyrie.decree = {"recruit": [bird_card, -101], "move": [off_suit_card], "battle": [], "build": []}
    state.eyrie.decree_cards_remaining = {
        "recruit": [bird_card, -101],
        "move": [off_suit_card],
        "battle": [],
        "build": [],
    }
    for cid in state.board.clearings:
        state.board.warriors[cid][Faction.EYRIE] = 0
        state.board.buildings[cid][Faction.EYRIE] = [
            b for b in state.board.buildings[cid][Faction.EYRIE] if b != BuildingType.ROOST
        ]
    state.board.buildings[6][Faction.EYRIE].append(BuildingType.ROOST)  # fox clearing for recruit
    state.eyrie.warriors_in_supply = 20
    state.scores[Faction.EYRIE] = 4

    state.eyrie.birdsong_cards_added = 1
    engine.apply_action(EndPhase())  # birdsong -> daylight
    for _ in range(2):
        recruit = next(action for action in engine.get_valid_actions() if isinstance(action, Recruit))
        engine.apply_action(recruit)
    engine.apply_action(FallIntoTurmoil())

    assert state.scores[Faction.EYRIE] == 2
    assert bird_card in state.discard_pile
    assert off_suit_card in state.discard_pile
    assert all(card_id > 0 for cards in state.eyrie.decree.values() for card_id in cards)
    engine.apply_action(SelectEyrieLeader("despot"))
    assert state.turn.phase == Phase.EVENING
    assert all(not isinstance(action, Recruit) for action in engine.get_valid_actions())


def test_eyrie_does_not_reinitialize_decree_after_finishing_all_cards() -> None:
    engine = RootEngine(seed=52)
    while engine.get_state().turn.current_faction != Faction.EYRIE:
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
    state = engine.get_state()

    state.eyrie.decree = {"recruit": [4], "move": [-102], "battle": [], "build": [-104]}
    state.eyrie.decree_cards_remaining = {
        "recruit": [4],
        "move": [-102],
        "battle": [],
        "build": [-104],
    }
    state.eyrie.warriors_in_supply = 20
    state.eyrie.birdsong_cards_added = 1

    engine.apply_action(EndPhase())  # birdsong -> daylight
    recruit = next(action for action in engine.get_valid_actions() if isinstance(action, Recruit))
    engine.apply_action(recruit)
    move_source = next(action for action in engine.get_valid_actions() if isinstance(action, SelectMoveSource))
    engine.apply_action(move_source)
    destination_actions = [action for action in engine.get_valid_actions() if isinstance(action, SelectMoveDestination)]
    move_destination = max(destination_actions, key=lambda action: action.warriors)
    engine.apply_action(move_destination)
    build = next(action for action in engine.get_valid_actions() if isinstance(action, Build))
    engine.apply_action(build)

    actions = engine.get_valid_actions()
    assert any(isinstance(action, EndPhase) for action in actions)
    assert not any(isinstance(action, FallIntoTurmoil) for action in actions)


def test_eyrie_lords_of_the_forest_rules_ties_but_not_empty_clearings() -> None:
    engine = RootEngine(seed=43)
    state = engine.get_state()
    state.board.warriors[3][Faction.MARQUISE] = 1
    state.board.warriors[3][Faction.EYRIE] = 1
    state.board.warriors[6][Faction.MARQUISE] = 0
    state.board.warriors[6][Faction.EYRIE] = 0
    assert engine.get_observation(Faction.EYRIE).clearings[3].ruler == Faction.EYRIE
    assert engine.get_observation(Faction.EYRIE).clearings[6].ruler is None


def test_eyrie_disdain_for_trade_scores_one_for_item_craft() -> None:
    engine = RootEngine(seed=47)
    while engine.get_state().turn.current_faction != Faction.EYRIE:
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
        engine.apply_action(EndPhase())
    state = engine.get_state()
    anvil = next(cid for cid, card in state.cards.items() if card.name == "Anvil")
    state.eyrie.hand = [anvil]
    state.eyrie.birdsong_cards_added = 1
    state.board.buildings[1][Faction.EYRIE].append(BuildingType.ROOST)
    engine.apply_action(EndPhase())  # birdsong -> daylight
    before = state.scores[Faction.EYRIE]
    engine.apply_action(Craft(card_id=anvil))
    assert state.scores[Faction.EYRIE] == before + 1


def test_keep_blocks_non_marquise_piece_placement() -> None:
    engine = RootEngine(seed=53)
    state = engine.get_state()
    keep = state.marquise.keep_clearing
    assert keep is not None
    with pytest.raises(ValueError):
        eyrie_rules.apply_recruit(state, Recruit(clearing_id=keep))
    with pytest.raises(ValueError):
        eyrie_rules.apply_build(state, Build(clearing_id=keep, building_type=BuildingType.ROOST))


def test_keep_blocks_alliance_piece_placement_actions() -> None:
    engine = RootEngine(seed=211)
    _advance_to_alliance_birdsong(engine)
    state = engine.get_state()
    keep = state.marquise.keep_clearing
    assert keep is not None
    keep_suit = state.board.clearings[keep].suit
    if keep_suit not in {Suit.FOX, Suit.RABBIT, Suit.MOUSE}:
        pytest.skip("Keep clearing must be fox/rabbit/mouse for revolt test setup")

    state.board.tokens[keep][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    suit_supporters = [cid for cid, card in state.cards.items() if card.suit in (keep_suit, Suit.BIRD)]
    state.alliance.supporters = suit_supporters[:4]

    with pytest.raises(ValueError):
        alliance_rules.apply_spread_sympathy(state, SpreadSympathy(clearing_id=keep))
    with pytest.raises(ValueError):
        alliance_rules.apply_revolt(state, Revolt(clearing_id=keep))

    state.turn.phase = Phase.EVENING
    state.alliance.officers = 1
    state.board.warriors[keep][Faction.ALLIANCE] = 1
    with pytest.raises(ValueError):
        alliance_rules.apply_organize(state, Organize(clearing_id=keep))

    state.board.buildings[keep][Faction.ALLIANCE].append(BuildingType.BASE)
    with pytest.raises(ValueError):
        alliance_rules.apply_recruit(state, Recruit(clearing_id=keep))


def test_field_hospitals_spends_matching_card_and_moves_removed_warriors_to_keep() -> None:
    engine = RootEngine(seed=59)
    state = engine.get_state()
    keep = state.marquise.keep_clearing
    assert keep is not None
    battle_clearing = 2
    state.board.warriors[battle_clearing][Faction.MARQUISE] = 2
    state.board.warriors[battle_clearing][Faction.EYRIE] = 2
    fox_card = next(cid for cid, card in state.cards.items() if card.suit == state.board.clearings[battle_clearing].suit)
    state.marquise.hand = [fox_card]
    keep_before = state.board.warriors[keep][Faction.MARQUISE]
    combat_rules.resolve_basic_battle(state, Faction.EYRIE, Faction.MARQUISE, battle_clearing)
    assert fox_card in state.discard_pile
    assert state.board.warriors[keep][Faction.MARQUISE] == keep_before + 1


def test_alliance_crafting_uses_sympathy_tokens() -> None:
    engine = RootEngine(seed=61)
    state = engine.get_state()
    anvil = next(cid for cid, card in state.cards.items() if card.name == "Anvil")
    state.alliance.hand = [anvil]
    state.board.tokens[1][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    assert anvil in alliance_rules.legal_crafting_cards(state)


def test_alliance_supporters_capacity_without_base_is_five() -> None:
    engine = RootEngine(seed=67)
    state = engine.get_state()
    state.alliance.supporters = [1, 2, 3, 4, 5]
    card_id = 6
    assert alliance_rules.gain_supporter(state, card_id) is False
    assert card_id in state.discard_pile


def test_alliance_birdsong_offers_revolt_and_sympathy_actions() -> None:
    engine = RootEngine(seed=71)
    _advance_to_alliance_birdsong(engine)
    state = engine.get_state()
    state.board.tokens[2][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    bird_supporters = [cid for cid, card in state.cards.items() if card.suit == Suit.BIRD][:2]
    state.alliance.supporters = list(bird_supporters)

    actions = engine.get_valid_actions()
    assert any(isinstance(a, Revolt) and a.clearing_id == 2 for a in actions)
    assert any(isinstance(a, SpreadSympathy) for a in actions)


def test_alliance_revolt_removes_enemy_pieces_places_base_and_officer() -> None:
    engine = RootEngine(seed=73)
    _advance_to_alliance_birdsong(engine)
    state = engine.get_state()
    state.board.tokens[2][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    state.board.tokens[5][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    state.alliance.sympathy_in_supply = 8
    rabbit_supporters = [cid for cid, card in state.cards.items() if card.suit == Suit.RABBIT][:2]
    state.alliance.supporters = list(rabbit_supporters)
    state.board.warriors[2][Faction.MARQUISE] = 2
    state.board.buildings[2][Faction.MARQUISE].append(BuildingType.SAWMILL)
    state.board.tokens[2][Faction.MARQUISE].append(TokenType.WOOD)
    before_score = state.scores[Faction.ALLIANCE]

    engine.apply_action(Revolt(clearing_id=2))

    assert state.alliance.bases[Suit.RABBIT] is True
    assert BuildingType.BASE in state.board.buildings[2][Faction.ALLIANCE]
    assert state.board.warriors[2][Faction.MARQUISE] == 0
    assert state.board.buildings[2][Faction.MARQUISE] == []
    assert state.board.tokens[2][Faction.MARQUISE] == []
    assert state.board.warriors[2][Faction.ALLIANCE] == 2
    assert state.alliance.officers == 1
    assert state.scores[Faction.ALLIANCE] == before_score + 3


def test_alliance_spread_sympathy_accounts_for_martial_law_cost() -> None:
    engine = RootEngine(seed=79)
    _advance_to_alliance_birdsong(engine)
    state = engine.get_state()
    state.board.tokens[2][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    state.alliance.sympathy_in_supply = 9
    mouse_supporters = [cid for cid, card in state.cards.items() if card.suit == Suit.MOUSE][:3]
    state.alliance.supporters = list(mouse_supporters)
    state.board.warriors[3][Faction.MARQUISE] = 3
    before_score = state.scores[Faction.ALLIANCE]

    engine.apply_action(SpreadSympathy(clearing_id=3))

    assert TokenType.SYMPATHY in state.board.tokens[3][Faction.ALLIANCE]
    assert len(state.alliance.supporters) == 1
    assert state.scores[Faction.ALLIANCE] == before_score + 1


def test_alliance_can_spread_sympathy_multiple_times_in_birdsong_if_legal() -> None:
    engine = RootEngine(seed=83)
    _advance_to_alliance_birdsong(engine)
    state = engine.get_state()
    bird_supporters = [cid for cid, card in state.cards.items() if card.suit == Suit.BIRD][:5]
    state.alliance.supporters = list(bird_supporters)
    state.alliance.sympathy_in_supply = 10

    first_spread = next(a for a in engine.get_valid_actions() if isinstance(a, SpreadSympathy))
    engine.apply_action(first_spread)
    assert engine.get_state().turn.phase == Phase.BIRDSONG
    assert any(isinstance(a, SpreadSympathy) for a in engine.get_valid_actions())

    second_spread = next(a for a in engine.get_valid_actions() if isinstance(a, SpreadSympathy))
    engine.apply_action(second_spread)
    assert engine.get_state().turn.phase == Phase.BIRDSONG


def test_alliance_spread_sympathy_cost_uses_tokens_on_map_not_supply_counter() -> None:
    engine = RootEngine(seed=89)
    _advance_to_alliance_birdsong(engine)
    state = engine.get_state()
    state.board.tokens[2][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    # Simulate an out-of-sync counter from previous effects/edits.
    state.alliance.sympathy_in_supply = 6
    bird_supporters = [cid for cid, card in state.cards.items() if card.suit == Suit.BIRD][:2]
    state.alliance.supporters = list(bird_supporters)

    legal_spread_clearings = {a.clearing_id for a in engine.get_valid_actions() if isinstance(a, SpreadSympathy)}
    assert 3 in legal_spread_clearings


@pytest.mark.parametrize(
    ("tokens_on_map", "expected_cost"),
    [
        (0, 1),
        (2, 1),
        (3, 2),
        (5, 2),
        (6, 3),
        (9, 3),
    ],
)
def test_alliance_sympathy_cost_track_by_tokens_on_map(tokens_on_map: int, expected_cost: int) -> None:
    engine = RootEngine(seed=97)
    state = engine.get_state()
    state.alliance.supporters = []
    suit = state.board.clearings[1].suit
    matching_supporters = [cid for cid, card in state.cards.items() if card.suit in (suit, Suit.BIRD)]
    state.alliance.supporters = matching_supporters[:expected_cost]
    for cid in range(1, 1 + tokens_on_map):
        state.board.tokens[cid][Faction.ALLIANCE].append(TokenType.SYMPATHY)

    assert alliance_rules._sympathy_supporter_cost(state) == expected_cost


@pytest.mark.parametrize(
    ("tokens_on_map", "expected_vp_reward"),
    [
        (1, 0),
        (2, 1),
        (4, 1),
        (5, 2),
        (6, 2),
        (7, 3),
        (8, 4),
        (10, 4),
    ],
)
def test_alliance_sympathy_vp_track_progression(tokens_on_map: int, expected_vp_reward: int) -> None:
    engine = RootEngine(seed=101)
    state = engine.get_state()
    for cid in range(1, 1 + tokens_on_map):
        state.board.tokens[cid][Faction.ALLIANCE].append(TokenType.SYMPATHY)

    assert alliance_rules._sympathy_vp_reward(state) == expected_vp_reward


def test_alliance_daylight_offers_craft_mobilize_and_train() -> None:
    engine = RootEngine(seed=103)
    _advance_to_alliance_birdsong(engine)
    state = engine.get_state()
    craft_card = next(cid for cid, card in state.cards.items() if card.name == "A Visit to Friends")
    rabbit_card = next(cid for cid, card in state.cards.items() if card.suit == Suit.RABBIT and cid != craft_card)
    state.alliance.hand = [craft_card, rabbit_card]
    state.board.tokens[2][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    state.board.buildings[2][Faction.ALLIANCE].append(BuildingType.BASE)
    state.alliance.bases[Suit.RABBIT] = True

    engine.apply_action(EndPhase())
    actions = engine.get_valid_actions()
    assert any(isinstance(action, Craft) and action.card_id == craft_card for action in actions)
    assert any(isinstance(action, Mobilize) and action.card_id == rabbit_card for action in actions)
    assert any(isinstance(action, Train) and action.card_id == rabbit_card for action in actions)


def test_alliance_evening_military_operations_limited_by_officers() -> None:
    engine = RootEngine(seed=107)
    _advance_to_alliance_birdsong(engine)
    state = engine.get_state()
    state.alliance.officers = 1
    state.board.warriors[2][Faction.ALLIANCE] = 1
    state.board.warriors[2][Faction.MARQUISE] = 1
    state.board.tokens[2][Faction.ALLIANCE] = [
        token for token in state.board.tokens[2][Faction.ALLIANCE] if token != TokenType.SYMPATHY
    ]

    engine.apply_action(EndPhase())  # to Daylight
    engine.apply_action(EndPhase())  # to Evening
    assert any(isinstance(action, Organize) for action in engine.get_valid_actions())
    engine.apply_action(Organize(clearing_id=2))
    assert state.alliance.military_ops_used == 1
    assert engine.get_valid_actions() == [EndPhase()]


def test_alliance_evening_draws_one_plus_number_of_bases() -> None:
    engine = RootEngine(seed=109)
    _advance_to_alliance_birdsong(engine)
    state = engine.get_state()
    state.alliance.bases[Suit.FOX] = True
    state.alliance.bases[Suit.RABBIT] = True

    engine.apply_action(EndPhase())  # to Daylight
    engine.apply_action(EndPhase())  # to Evening
    before_hand = len(state.alliance.hand)
    engine.apply_action(EndPhase())  # end Alliance evening

    assert len(state.alliance.hand) == before_hand + 3


def test_defenseless_battle_removes_sympathy_without_attacker_loss() -> None:
    engine = RootEngine(seed=701)
    state = engine.get_state()
    before_score = state.scores[Faction.MARQUISE]
    state.board.warriors[2][Faction.MARQUISE] = 1
    state.board.warriors[2][Faction.ALLIANCE] = 0
    state.board.tokens[2][Faction.ALLIANCE] = [TokenType.SYMPATHY]

    combat_rules.resolve_basic_battle(state, Faction.MARQUISE, Faction.ALLIANCE, 2)

    assert state.board.warriors[2][Faction.MARQUISE] == 1
    assert TokenType.SYMPATHY not in state.board.tokens[2][Faction.ALLIANCE]
    assert state.scores[Faction.MARQUISE] == before_score + 1


def test_battle_only_scores_for_cardboard_not_warriors() -> None:
    engine = RootEngine(seed=704)
    state = engine.get_state()
    before_score = state.scores[Faction.MARQUISE]
    state.board.warriors[2][Faction.MARQUISE] = 1
    state.board.warriors[2][Faction.EYRIE] = 1

    combat_rules.resolve_basic_battle(state, Faction.MARQUISE, Faction.EYRIE, 2)

    assert state.board.warriors[2][Faction.EYRIE] == 0
    assert state.scores[Faction.MARQUISE] == before_score


def test_outrage_on_move_into_sympathetic_clearing_spends_matching_card() -> None:
    engine = RootEngine(seed=702)
    state = engine.get_state()
    mouse_card = next(cid for cid, c in state.cards.items() if c.suit == Suit.MOUSE)
    rabbit_card = next(cid for cid, c in state.cards.items() if c.suit == Suit.RABBIT)
    state.marquise.hand = [rabbit_card, mouse_card]
    state.board.tokens[3][Faction.ALLIANCE].append(TokenType.SYMPATHY)  # clearing 3 is mouse
    state.board.warriors[1][Faction.MARQUISE] = 1
    state.decision_context.selected_source = 1

    marquise_rules.apply_move_destination(state, SelectMoveDestination(clearing_id=3))

    assert mouse_card not in state.marquise.hand
    assert mouse_card in state.alliance.supporters


def test_outrage_on_sympathy_removal_draws_when_no_matching_cards() -> None:
    engine = RootEngine(seed=703)
    state = engine.get_state()
    state.marquise.hand = []
    state.draw_pile = [state.draw_pile[-1]]
    top_card = state.draw_pile[-1]
    state.board.warriors[2][Faction.MARQUISE] = 1
    state.board.tokens[2][Faction.ALLIANCE] = [TokenType.SYMPATHY]

    combat_rules.resolve_basic_battle(state, Faction.MARQUISE, Faction.ALLIANCE, 2)

    assert top_card in state.alliance.supporters


def test_favor_scores_for_removed_tokens_and_buildings() -> None:
    marquise_engine = RootEngine(seed=801)
    marquise_state = marquise_engine.get_state()
    for cid, clearing in marquise_state.board.clearings.items():
        if clearing.suit == Suit.MOUSE:
            marquise_state.board.buildings[cid][Faction.EYRIE].clear()
            marquise_state.board.buildings[cid][Faction.ALLIANCE].clear()
            marquise_state.board.tokens[cid][Faction.ALLIANCE] = [
                token for token in marquise_state.board.tokens[cid][Faction.ALLIANCE] if token != TokenType.SYMPATHY
            ]
    marquise_state.board.clearings[2].suit = Suit.MOUSE
    marquise_state.board.buildings[2][Faction.EYRIE].append(BuildingType.ROOST)
    marquise_state.board.tokens[2][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    expected_marquise_delta = sum(
        len(marquise_state.board.buildings[cid][Faction.EYRIE])
        + len(marquise_state.board.buildings[cid][Faction.ALLIANCE])
        + sum(1 for token in marquise_state.board.tokens[cid][Faction.ALLIANCE] if token == TokenType.SYMPATHY)
        for cid, clearing in marquise_state.board.clearings.items()
        if clearing.suit == Suit.MOUSE
    )
    before_marquise_score = marquise_state.scores[Faction.MARQUISE]
    marquise_rules._resolve_favor(marquise_state, Suit.MOUSE)
    assert marquise_state.scores[Faction.MARQUISE] == before_marquise_score + expected_marquise_delta

    eyrie_engine = RootEngine(seed=802)
    eyrie_state = eyrie_engine.get_state()
    for cid, clearing in eyrie_state.board.clearings.items():
        if clearing.suit == Suit.MOUSE:
            eyrie_state.board.buildings[cid][Faction.MARQUISE].clear()
            eyrie_state.board.buildings[cid][Faction.ALLIANCE].clear()
            eyrie_state.board.tokens[cid][Faction.MARQUISE] = [
                token for token in eyrie_state.board.tokens[cid][Faction.MARQUISE] if token != TokenType.KEEP
            ]
            eyrie_state.board.tokens[cid][Faction.ALLIANCE] = [
                token for token in eyrie_state.board.tokens[cid][Faction.ALLIANCE] if token != TokenType.SYMPATHY
            ]
    eyrie_state.board.clearings[2].suit = Suit.MOUSE
    eyrie_state.board.buildings[2][Faction.MARQUISE].append(BuildingType.SAWMILL)
    eyrie_state.board.tokens[2][Faction.ALLIANCE].append(TokenType.SYMPATHY)
    expected_eyrie_delta = sum(
        len(eyrie_state.board.buildings[cid][Faction.MARQUISE])
        + len(eyrie_state.board.buildings[cid][Faction.ALLIANCE])
        + sum(1 for token in eyrie_state.board.tokens[cid][Faction.MARQUISE] if token == TokenType.KEEP)
        + sum(1 for token in eyrie_state.board.tokens[cid][Faction.ALLIANCE] if token == TokenType.SYMPATHY)
        for cid, clearing in eyrie_state.board.clearings.items()
        if clearing.suit == Suit.MOUSE
    )
    before_eyrie_score = eyrie_state.scores[Faction.EYRIE]
    eyrie_rules._resolve_favor(eyrie_state, Suit.MOUSE)
    assert eyrie_state.scores[Faction.EYRIE] == before_eyrie_score + expected_eyrie_delta

    alliance_engine = RootEngine(seed=803)
    alliance_state = alliance_engine.get_state()
    for cid, clearing in alliance_state.board.clearings.items():
        if clearing.suit == Suit.MOUSE:
            alliance_state.board.buildings[cid][Faction.MARQUISE].clear()
            alliance_state.board.buildings[cid][Faction.EYRIE].clear()
            alliance_state.board.tokens[cid][Faction.MARQUISE] = [
                token for token in alliance_state.board.tokens[cid][Faction.MARQUISE] if token != TokenType.WOOD
            ]
    alliance_state.board.clearings[2].suit = Suit.MOUSE
    alliance_state.board.buildings[2][Faction.MARQUISE].append(BuildingType.SAWMILL)
    alliance_state.board.tokens[2][Faction.MARQUISE].append(TokenType.WOOD)
    expected_alliance_delta = sum(
        len(alliance_state.board.buildings[cid][Faction.MARQUISE])
        + len(alliance_state.board.buildings[cid][Faction.EYRIE])
        + sum(1 for token in alliance_state.board.tokens[cid][Faction.MARQUISE] if token == TokenType.WOOD)
        for cid, clearing in alliance_state.board.clearings.items()
        if clearing.suit == Suit.MOUSE
    )
    before_alliance_score = alliance_state.scores[Faction.ALLIANCE]
    alliance_rules._resolve_favor(alliance_state, Suit.MOUSE)
    assert alliance_state.scores[Faction.ALLIANCE] == before_alliance_score + expected_alliance_delta


def test_marquise_ai_toggle_off_has_no_autoplay() -> None:
    engine = RootEngine(seed=31, marquise_ai_enabled=False)
    state = engine.get_state()

    assert state.turn.current_faction == Faction.MARQUISE
    assert state.turn.phase == Phase.BIRDSONG


def test_marquise_ai_autoplays_until_turn_ends_when_enabled() -> None:
    engine = RootEngine(seed=31, marquise_ai_enabled=True)
    state = engine.get_state()

    assert state.turn.current_faction != Faction.MARQUISE
