"""Cross-faction phase and turn progression rules."""

from __future__ import annotations

from ..enums import BuildingType, DecisionType, Faction, Phase, TokenType
from ..models import GameState
from .crafting import initialize_marquise_crafting_power
from .eyrie import roost_draw_bonus
from .marquise import recruiter_draw_bonus


def advance_phase(state: GameState) -> None:
    """Move from birdsong->daylight->evening->next faction."""

    if state.turn.phase == Phase.BIRDSONG:
        _resolve_birdsong_effects(state)
        state.turn.phase = Phase.DAYLIGHT
        _on_daylight_start(state)
    elif state.turn.phase == Phase.DAYLIGHT:
        state.turn.phase = Phase.EVENING
    else:
        _resolve_evening_effects(state)
        _advance_to_next_faction(state)
    state.decision_context = state.decision_context.__class__(decision_type=DecisionType.MAIN_ACTION)


def _advance_to_next_faction(state: GameState) -> None:
    order = state.turn.turn_order
    idx = order.index(state.turn.current_faction)
    nxt = (idx + 1) % len(order)
    if nxt == 0:
        state.turn.round_number += 1
    state.turn.current_faction = order[nxt]
    state.turn.phase = Phase.BIRDSONG
    if state.turn.current_faction == Faction.EYRIE:
        state.eyrie.birdsong_cards_added = 0


def _resolve_birdsong_effects(state: GameState) -> None:
    if state.turn.current_faction != Faction.MARQUISE:
        return
    for cid in state.board.clearings:
        sawmills = sum(
            1
            for building in state.board.buildings[cid][Faction.MARQUISE]
            if building == BuildingType.SAWMILL
        )
        state.board.tokens[cid][Faction.MARQUISE].extend([TokenType.WOOD] * sawmills)


def _on_daylight_start(state: GameState) -> None:
    if state.turn.current_faction == Faction.MARQUISE:
        state.marquise.daylight_actions_used = 0
        state.marquise.recruit_used_this_turn = False
        initialize_marquise_crafting_power(state)
        state.marquise.crafting_window_open = True
    elif state.turn.current_faction == Faction.EYRIE:
        state.eyrie.crafting_window_open = True
        state.eyrie.resolving_decree = False
        state.eyrie.decree_column_index = 0
        state.eyrie.decree_cards_remaining = {
            key: list(cards) for key, cards in state.eyrie.decree.items()
        }
    elif state.turn.current_faction == Faction.ALLIANCE:
        state.alliance.crafting_window_open = True
        state.alliance.military_ops_used = 0


def _resolve_evening_effects(state: GameState) -> None:
    faction_state = state.faction_state(state.turn.current_faction)
    draw_count = 1
    if state.turn.current_faction == Faction.MARQUISE:
        draw_count += recruiter_draw_bonus(state)
    elif state.turn.current_faction == Faction.EYRIE:
        draw_count += roost_draw_bonus(state)
    elif state.turn.current_faction == Faction.ALLIANCE:
        draw_count += sum(1 for built in state.alliance.bases.values() if built)
    _draw_cards(state, faction_state.hand, draw_count)
    while len(faction_state.hand) > 5:
        state.discard_pile.append(faction_state.hand.pop())


def _draw_cards(state: GameState, hand: list[int], count: int) -> None:
    for _ in range(count):
        if not state.draw_pile:
            if not state.discard_pile:
                return
            state.draw_pile = list(state.discard_pile)
            state.discard_pile.clear()
        hand.append(state.draw_pile.pop())
