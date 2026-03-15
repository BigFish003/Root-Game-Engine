from __future__ import annotations

from root_engine.engine import RootEngine
from root_engine.enums import Faction
from root_engine.render import TextRenderer, VisualRenderer, get_renderer
from root_engine.renderer import RootRenderer


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


def test_renderer_factory_returns_requested_renderers() -> None:
    assert isinstance(get_renderer("text"), TextRenderer)
    assert isinstance(get_renderer("visual"), VisualRenderer)
