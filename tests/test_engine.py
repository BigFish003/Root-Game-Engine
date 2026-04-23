from __future__ import annotations

import pytest

from root_engine.actions import Build, Craft, EndPhase, Recruit, SelectMoveDestination, SelectMoveSource
from root_engine.engine import RootEngine
from root_engine.enums import BuildingType, DecisionType, Faction, Phase, Suit


def test_reset_initial_state_has_expected_markers() -> None:
    engine = RootEngine(seed=7)
    state = engine.get_state()

    assert state.turn.current_faction == Faction.MARQUISE
    assert state.turn.phase == Phase.BIRDSONG
    assert state.marquise.keep_clearing == 1
    assert state.board.warriors[12][Faction.EYRIE] == 6


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
    assert engine.get_state().scores[Faction.MARQUISE] == before_score + 2


def test_atomic_move_selection_changes_context_and_board() -> None:
    engine = RootEngine(seed=4)
    engine.apply_action(EndPhase())

    select_source = next(a for a in engine.get_valid_actions() if isinstance(a, SelectMoveSource))
    src = select_source.clearing_id
    src_before = engine.get_state().board.warriors[src][Faction.MARQUISE]
    engine.apply_action(select_source)

    assert engine.get_state().decision_context.decision_type == DecisionType.SELECT_MOVE_DESTINATION
    dest_action = next(a for a in engine.get_valid_actions() if isinstance(a, SelectMoveDestination))
    dest = dest_action.clearing_id
    dest_before = engine.get_state().board.warriors[dest][Faction.MARQUISE]

    engine.apply_action(dest_action)
    assert engine.get_state().board.warriors[src][Faction.MARQUISE] == src_before - 1
    assert engine.get_state().board.warriors[dest][Faction.MARQUISE] == dest_before + 1
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
