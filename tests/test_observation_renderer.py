from __future__ import annotations

from PIL import Image

from root_engine.engine import RootEngine
from root_engine.enums import Faction, ItemType, Suit, VagabondRelation
from root_engine.render import TextRenderer, VisualRenderer, get_renderer
from root_engine.renderer import RootRenderer
from state_renderer.render import state_renderer


def test_get_observation_hides_other_hands_and_shows_observer_hand() -> None:
    engine = RootEngine(seed=13)

    obs = engine.get_observation(Faction.MARQUISE)

    assert obs.factions[Faction.MARQUISE].hand is not None
    assert obs.factions[Faction.EYRIE].hand is None
    assert obs.factions[Faction.EYRIE].hand_count == len(engine.get_state().eyrie.hand)


def test_get_observation_includes_public_board_and_turn_context() -> None:
    engine = RootEngine(seed=21)
    obs = engine.get_observation(Faction.ALLIANCE)

    assert 1 in obs.clearings
    assert obs.clearings[1].adjacent_clearings
    assert obs.current_faction == engine.get_state().turn.current_faction
    assert obs.current_phase == engine.get_state().turn.phase.value
    assert obs.scores == engine.get_state().scores


def test_renderer_renders_full_state_and_observation() -> None:
    engine = RootEngine(seed=33)
    renderer = RootRenderer()

    full = renderer.render(engine.get_state())
    marquise_obs = engine.get_observation(Faction.MARQUISE)
    partial = renderer.render(marquise_obs)

    assert "Faction boards:" in full
    assert "hand=[" in full
    assert "Observer: marquise" in partial
    assert "hidden(count=" in partial
    assert "Observer private info:" in partial
    assert "supporters:" not in partial


def test_visual_renderer_outputs_svg_and_respects_hidden_hands() -> None:
    engine = RootEngine(seed=99)
    renderer = VisualRenderer()

    full_svg = renderer.render(engine.get_state())
    marquise_obs = engine.get_observation(Faction.MARQUISE)
    obs_svg = renderer.render(marquise_obs)

    assert full_svg.startswith("<svg")
    assert "Faction Status" in full_svg
    assert "hidden(" not in full_svg
    assert "Observer: marquise" in obs_svg
    assert "hidden(" in obs_svg
    assert "Observer view" in obs_svg


def test_renderer_shows_alliance_supporters_only_for_alliance_observer() -> None:
    engine = RootEngine(seed=144)
    engine.get_state().alliance.supporters = [1, 2, 3]
    renderer = RootRenderer()

    marquise_view = renderer.render(engine.get_observation(Faction.MARQUISE))
    alliance_view = renderer.render(engine.get_observation(Faction.ALLIANCE))

    assert "supporters:" not in marquise_view
    assert "supporters: [1, 2, 3]" in alliance_view


def test_alliance_private_observation_includes_supporter_suits_by_id() -> None:
    engine = RootEngine(seed=145)
    state = engine.get_state()
    rabbit = next(cid for cid, card in state.cards.items() if card.suit == Suit.RABBIT)
    fox = next(cid for cid, card in state.cards.items() if card.suit == Suit.FOX and cid != rabbit)
    state.alliance.supporters = [rabbit, fox]

    obs = engine.get_observation(Faction.ALLIANCE)
    private_data = obs.factions[Faction.ALLIANCE].private_data

    assert private_data["supporters"] == [rabbit, fox]
    assert private_data["supporter_suits_by_id"] == {str(rabbit): "rabbit", str(fox): "fox"}


def test_eyrie_observation_exposes_decree_suits() -> None:
    engine = RootEngine(seed=55)
    state = engine.get_state()

    fox_card = next(cid for cid, card in state.cards.items() if card.suit == Suit.FOX)
    mouse_card = next(cid for cid, card in state.cards.items() if card.suit == Suit.MOUSE and cid != fox_card)
    state.eyrie.decree = {"recruit": [fox_card], "move": [mouse_card], "battle": [], "build": []}

    obs = engine.get_observation(Faction.MARQUISE)
    eyrie_public = obs.factions[Faction.EYRIE].public_data

    assert eyrie_public["decree"]["recruit"] == [fox_card]
    assert eyrie_public["decree_suits"]["recruit"] == ["fox"]
    assert eyrie_public["decree_suits"]["move"] == ["mouse"]


def test_visual_renderer_includes_vagabond_panel_for_state_and_observation() -> None:
    engine = RootEngine(seed=166)
    renderer = VisualRenderer()

    full_svg = renderer.render(engine.get_state())
    vagabond_obs_svg = renderer.render(engine.get_observation(Faction.VAGABOND))

    assert "Vagabond" in full_svg
    assert "Location: forest" in full_svg
    assert "Satchel:" in full_svg
    assert "Tracks:" in full_svg
    assert "Relations:" in full_svg
    assert "Quests:" in full_svg
    assert "Ruins:" in full_svg
    assert "Observer view" in vagabond_obs_svg
    assert "Satchel:" in vagabond_obs_svg


def test_observation_exposes_crafted_and_item_supply_state() -> None:
    engine = RootEngine(seed=167)
    state = engine.get_state()
    state.crafted_cards[Faction.MARQUISE] = [1]
    state.crafted_items[Faction.MARQUISE] = {ItemType.BOOT: 1}

    obs = engine.get_observation(Faction.EYRIE)
    marquise = obs.factions[Faction.MARQUISE]

    assert obs.item_supply["boot"] == state.item_supply[ItemType.BOOT]
    observed_forest = obs.forests[state.vagabond.forest_location]
    actual_forest = state.board.forests[state.vagabond.forest_location]
    assert observed_forest["adjacent_clearings"] == actual_forest.adjacent_clearings
    assert observed_forest["adjacent_forests"] == actual_forest.adjacent_forests
    assert marquise.crafted_cards == [1]
    assert marquise.crafted_items == {"boot": 1}
    assert marquise.public_data["crafted_cards"] == [1]
    assert marquise.public_data["crafted_items"] == {"boot": 1}


def test_text_and_svg_renderers_show_crafted_sections_and_vagabond_board() -> None:
    engine = RootEngine(seed=168)
    state = engine.get_state()
    state.vagabond.damaged_items[ItemType.SWORD] = 1
    state.vagabond.relationships[Faction.MARQUISE] = VagabondRelation.HOSTILE

    text = RootRenderer().render(engine.get_observation(Faction.VAGABOND))
    svg = VisualRenderer().render(engine.get_observation(Faction.VAGABOND))

    for faction in Faction:
        assert f"- {faction.value}:" in text
    assert text.count("Crafted Cards:") == len(Faction)
    assert text.count("Crafted Items:") == len(Faction)
    assert "Satchel:" in svg
    assert "Damaged:" in svg
    assert "Relations:" in svg


def test_pil_renderer_handles_vagabond_clearing_and_forest_locations(tmp_path) -> None:
    engine = RootEngine(seed=169)
    render = state_renderer()
    state = engine.get_state()
    state.vagabond.location = 6
    state.vagabond.forest_location = None

    clearing_path = tmp_path / "vagabond_clearing.png"
    render.render_board(engine.get_observation(Faction.VAGABOND), str(clearing_path))
    with Image.open(clearing_path) as image:
        assert image.size == (1600, 1200)

    state.vagabond.location = 0
    state.vagabond.forest_location = 5
    forest_path = tmp_path / "vagabond_forest.png"
    render.render_board(engine.get_observation(Faction.VAGABOND), str(forest_path))
    with Image.open(forest_path) as image:
        assert image.size == (1600, 1200)


def test_renderer_factory_returns_requested_renderers() -> None:
    assert isinstance(get_renderer("text"), TextRenderer)
    assert isinstance(get_renderer("visual"), VisualRenderer)
