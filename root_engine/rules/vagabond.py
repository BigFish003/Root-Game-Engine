"""Vagabond legal action generation and application."""

from __future__ import annotations

from ..actions import (
    Craft,
    EndPhase,
    SelectBattleClearing,
    SelectBattleTarget,
    VagabondAid,
    VagabondExplore,
    VagabondMove,
    VagabondQuest,
    VagabondRepair,
    VagabondSlip,
    VagabondSpecial,
    VagabondStrike,
)
from ..enums import (
    CardTag,
    DecisionType,
    Faction,
    ItemType,
    Phase,
    Suit,
    TokenType,
    VagabondRelation,
)
from ..models import GameState
from . import alliance as alliance_rules
from .pieces import return_building_to_supply, return_token_to_supply

TRACK_ITEMS = {ItemType.TEAPOT, ItemType.COIN, ItemType.BAG}
SATCHEL_ITEMS = {
    ItemType.BOOT,
    ItemType.SWORD,
    ItemType.TORCH,
    ItemType.HAMMER,
    ItemType.CROSSBOW,
}
AID_THRESHOLDS = {
    VagabondRelation.INDIFFERENT: (1, VagabondRelation.AMIABLE, 1),
    VagabondRelation.AMIABLE: (2, VagabondRelation.FRIENDLY, 2),
    VagabondRelation.FRIENDLY: (3, VagabondRelation.FRIENDLY, 2),
}


def valid_actions(state: GameState) -> list:
    """Return legal next actions for the Vagabond."""

    if state.turn.phase == Phase.BIRDSONG:
        if state.decision_context.selected_destination is not None:
            return [EndPhase()]
        return [EndPhase(), *[VagabondSlip(dest) for dest in _slip_destinations(state)]]
    if state.turn.phase == Phase.EVENING:
        return [EndPhase()]

    ctx = state.decision_context
    if (
        ctx.decision_type == DecisionType.SELECT_BATTLE_TARGET
        and ctx.selected_battle_clearing is not None
    ):
        return [
            SelectBattleTarget(f.value)
            for f in _battle_targets(state, ctx.selected_battle_clearing)
        ]

    actions: list = [EndPhase()]
    actions.extend(VagabondMove(dest) for dest in _move_destinations(state))
    actions.extend(
        VagabondExplore(state.vagabond.location) for _ in [0] if _can_explore(state)
    )
    actions.extend(_aid_actions(state))
    actions.extend(
        VagabondQuest(qid, draw_cards=False) for qid in _completable_quests(state)
    )
    actions.extend(
        VagabondQuest(qid, draw_cards=True) for qid in _completable_quests(state)
    )
    if _ready_count(state, ItemType.CROSSBOW) > 0:
        actions.extend(VagabondStrike(f) for f in _piece_factions_at_location(state))
    if _ready_count(state, ItemType.HAMMER) > 0:
        actions.extend(
            VagabondRepair(item)
            for item, count in state.vagabond.damaged_items.items()
            if count > 0
        )
    if _ready_count(state, ItemType.SWORD) > 0:
        battle_clearings = _battle_clearings(state)
        actions.extend(SelectBattleClearing(cid) for cid in battle_clearings)
    if _ready_count(state, ItemType.HAMMER) > 0:
        actions.extend(Craft(card_id) for card_id in _legal_craft_cards(state))
    if _ready_count(state, ItemType.TORCH) > 0:
        actions.extend(_special_actions(state))
    return actions


def apply_slip(state: GameState, action: VagabondSlip) -> None:
    state.vagabond.location = action.destination
    state.decision_context.selected_destination = action.destination


def apply_move(state: GameState, action: VagabondMove) -> None:
    cost = 1 + (1 if _has_hostile_warrior(state, action.destination) else 0)
    _exhaust(state, ItemType.BOOT, cost)
    state.vagabond.location = action.destination
    alliance_rules.trigger_outrage(state, Faction.VAGABOND, action.destination)


def apply_explore(state: GameState, action: VagabondExplore) -> None:
    if action.clearing_id != state.vagabond.location:
        raise ValueError("Vagabond can explore only in his clearing")
    items = state.board.ruin_items.get(action.clearing_id, [])
    if not items:
        raise ValueError("No ruin item to explore")
    _exhaust(state, ItemType.TORCH, 1)
    _gain_item(state, items.pop(0))
    state.scores[Faction.VAGABOND] += 1
    if not items:
        state.board.ruin_items.pop(action.clearing_id, None)
        state.board.clearings[action.clearing_id].has_ruin = False


def apply_aid(state: GameState, action: VagabondAid) -> None:
    loc = _require_clearing_location(state)
    if action.card_id not in state.vagabond.hand:
        raise ValueError("Card not in Vagabond hand")
    card = state.cards[action.card_id]
    if card.suit not in (Suit.BIRD, state.board.clearings[loc].suit):
        raise ValueError("Aid card must match clearing or be bird")
    if not _faction_has_piece(state, loc, action.target_faction):
        raise ValueError("Aid target must have a piece in the clearing")
    _exhaust(state, action.exhausted_item, 1)
    state.vagabond.hand.remove(action.card_id)
    state.faction_state(action.target_faction).hand.append(action.card_id)
    crafted = state.crafted_items.setdefault(action.target_faction, {})
    for item, count in list(crafted.items()):
        if count > 0:
            crafted[item] -= 1
            _gain_item(state, item)
            break
    _improve_relationship_from_aid(state, action.target_faction)


def apply_quest(state: GameState, action: VagabondQuest) -> None:
    quest = state.quests[action.quest_id]
    for item in quest["items"]:
        _exhaust(state, item, 1)
    state.vagabond.quests_available.remove(action.quest_id)
    state.vagabond.quests_completed.append(action.quest_id)
    if state.quest_deck:
        state.vagabond.quests_available.append(state.quest_deck.pop())
    if action.draw_cards:
        _draw_cards(state, state.vagabond.hand, 2)
    else:
        suit = quest["suit"]
        state.scores[Faction.VAGABOND] += sum(
            1
            for qid in state.vagabond.quests_completed
            if state.quests[qid]["suit"] == suit
        )


def apply_strike(state: GameState, action: VagabondStrike) -> None:
    loc = _require_clearing_location(state)
    _exhaust(state, ItemType.CROSSBOW, 1)
    if state.board.warriors[loc][action.target_faction] > 0:
        state.board.warriors[loc][action.target_faction] -= 1
        _removed_piece(state, action.target_faction, in_battle=False, warrior=True)
        return
    if state.board.tokens[loc][action.target_faction]:
        token = state.board.tokens[loc][action.target_faction].pop()
        return_token_to_supply(state, action.target_faction, token)
        state.scores[Faction.VAGABOND] += 1
        _removed_piece(state, action.target_faction, in_battle=False, warrior=False)
        if token == TokenType.SYMPATHY:
            alliance_rules.trigger_outrage(
                state, Faction.VAGABOND, loc, require_sympathy_present=False
            )
        return
    if state.board.buildings[loc][action.target_faction]:
        building = state.board.buildings[loc][action.target_faction].pop()
        return_building_to_supply(state, action.target_faction, building, loc)
        state.scores[Faction.VAGABOND] += 1
        _removed_piece(state, action.target_faction, in_battle=False, warrior=False)


def apply_repair(state: GameState, action: VagabondRepair) -> None:
    _exhaust(state, ItemType.HAMMER, 1)
    _move_count(state.vagabond.damaged_items, action.damaged_item, -1)
    _gain_item(state, action.damaged_item)


def apply_battle_select_clearing(
    state: GameState, action: SelectBattleClearing
) -> None:
    state.decision_context.decision_type = DecisionType.SELECT_BATTLE_TARGET
    state.decision_context.selected_battle_clearing = action.clearing_id


def apply_battle_select_target(state: GameState, action: SelectBattleTarget) -> None:
    loc = state.decision_context.selected_battle_clearing
    if loc is None:
        raise ValueError("No battle clearing selected")
    defender = Faction(action.target_faction)
    _exhaust(state, ItemType.SWORD, 1)
    hits = min(
        max(1, _undamaged_total(state, ItemType.SWORD)),
        _defender_piece_count(state, loc, defender),
    )
    defender_had_warriors = state.board.warriors[loc][defender] > 0
    first_hostile_warrior = (
        state.vagabond.relationships.get(defender) != VagabondRelation.HOSTILE
    )
    warriors_removed = min(hits, state.board.warriors[loc][defender])
    state.board.warriors[loc][defender] -= warriors_removed
    for idx in range(warriors_removed):
        _removed_piece(
            state,
            defender,
            in_battle=True,
            warrior=True,
            score_infamy=not (first_hostile_warrior and idx == 0),
        )
    remaining = hits - warriors_removed
    while remaining > 0 and state.board.tokens[loc][defender]:
        token = state.board.tokens[loc][defender].pop()
        return_token_to_supply(state, defender, token)
        state.scores[Faction.VAGABOND] += 1
        _removed_piece(state, defender, in_battle=True, warrior=False)
        if token == TokenType.SYMPATHY:
            alliance_rules.trigger_outrage(
                state, Faction.VAGABOND, loc, require_sympathy_present=False
            )
        remaining -= 1
    while remaining > 0 and state.board.buildings[loc][defender]:
        building = state.board.buildings[loc][defender].pop()
        return_building_to_supply(state, defender, building, loc)
        state.scores[Faction.VAGABOND] += 1
        _removed_piece(state, defender, in_battle=True, warrior=False)
        remaining -= 1
    defender_hits = 1 if defender_had_warriors else 0
    for _ in range(defender_hits):
        _damage_one_item(state)
    state.decision_context.decision_type = DecisionType.MAIN_ACTION
    state.decision_context.selected_battle_clearing = None


def apply_craft(state: GameState, action: Craft) -> None:
    if action.card_id not in state.vagabond.hand:
        raise ValueError("Card not in hand")
    if action.card_id not in _legal_craft_cards(state):
        raise ValueError("Vagabond cannot craft this card")
    card = state.cards[action.card_id]
    hammer_cost = sum(card.craft_cost.values()) + card.craft_cost_any
    _exhaust(state, ItemType.HAMMER, hammer_cost)
    state.vagabond.hand.remove(action.card_id)
    if card.vp_on_craft > 0:
        state.scores[Faction.VAGABOND] += card.vp_on_craft
    if CardTag.ITEM in card.tags:
        _gain_item(state, _item_from_card_name(card.name))
    elif CardTag.PERSISTENT_EFFECT in card.tags:
        state.vagabond.crafted_effects.append(card.name)
    else:
        state.discard_pile.append(action.card_id)


def apply_special(state: GameState, action: VagabondSpecial) -> None:
    _exhaust(state, ItemType.TORCH, 1)
    if state.vagabond.character == "thief" and action.target_faction is not None:
        hand = state.faction_state(action.target_faction).hand
        if hand:
            state.vagabond.hand.append(hand.pop(0))
    elif state.vagabond.character == "tinker":
        loc = _require_clearing_location(state)
        suit = state.board.clearings[loc].suit
        for card_id in list(reversed(state.discard_pile)):
            if state.cards[card_id].suit in (suit, Suit.BIRD):
                state.discard_pile.remove(card_id)
                state.vagabond.hand.append(card_id)
                break
    elif state.vagabond.character == "ranger":
        for item in list(state.vagabond.damaged_items):
            if state.vagabond.damaged_items.get(item, 0) <= 0:
                continue
            _move_count(state.vagabond.damaged_items, item, -1)
            _gain_item(state, item)
            if sum(state.vagabond.damaged_items.values()) == 0:
                break


def refresh_items(state: GameState) -> None:
    refresh_count = 3 + 2 * state.vagabond.tracks.get(ItemType.TEAPOT, 0)
    for pool_name in ("exhausted_tracks", "exhausted_items"):
        pool = getattr(state.vagabond, pool_name)
        for item in list(pool):
            while pool.get(item, 0) > 0 and refresh_count > 0:
                _move_count(pool, item, -1)
                _gain_item(state, item)
                refresh_count -= 1


def evening_rest_and_draw(state: GameState) -> int:
    if state.vagabond.location == 0:
        for item in list(state.vagabond.damaged_items):
            while state.vagabond.damaged_items.get(item, 0) > 0:
                _move_count(state.vagabond.damaged_items, item, -1)
                _gain_item(state, item)
    return 1 + state.vagabond.tracks.get(ItemType.COIN, 0)


def enforce_item_capacity(state: GameState) -> None:
    limit = 6 + 2 * state.vagabond.tracks.get(ItemType.BAG, 0)
    while (
        sum(state.vagabond.satchel.values())
        + sum(state.vagabond.damaged_items.values())
        > limit
    ):
        pool = (
            state.vagabond.damaged_items
            if state.vagabond.damaged_items
            else state.vagabond.satchel
        )
        item = next(iter(pool))
        _move_count(pool, item, -1)


def _slip_destinations(state: GameState) -> list[int]:
    loc = state.vagabond.location
    if loc == 0 or loc is None:
        return sorted(state.board.clearings)
    return [0, *state.board.clearings[loc].adjacent_clearings]


def _move_destinations(state: GameState) -> list[int]:
    loc = state.vagabond.location
    if loc == 0 or loc is None:
        return (
            sorted(state.board.clearings)
            if _ready_count(state, ItemType.BOOT) > 0
            else []
        )
    if _ready_count(state, ItemType.BOOT) <= 0:
        return []
    return [
        dest
        for dest in state.board.clearings[loc].adjacent_clearings
        if _ready_count(state, ItemType.BOOT)
        >= (1 + (1 if _has_hostile_warrior(state, dest) else 0))
    ]


def _can_explore(state: GameState) -> bool:
    loc = state.vagabond.location
    return (
        loc in state.board.ruin_items
        and bool(state.board.ruin_items[loc])
        and _ready_count(state, ItemType.TORCH) > 0
    )


def _aid_actions(state: GameState) -> list[VagabondAid]:
    loc = state.vagabond.location
    if loc == 0 or loc is None:
        return []
    suit = state.board.clearings[loc].suit
    cards = [
        cid for cid in state.vagabond.hand if state.cards[cid].suit in (suit, Suit.BIRD)
    ]
    ready_items = [item for item, count in _ready_items(state).items() if count > 0]
    return [
        VagabondAid(f, cid, item)
        for f in _piece_factions_at_location(state)
        for cid in cards
        for item in ready_items
    ]


def _completable_quests(state: GameState) -> list[str]:
    loc = state.vagabond.location
    if loc == 0 or loc is None:
        return []
    suit = state.board.clearings[loc].suit
    result = []
    for qid in state.vagabond.quests_available:
        quest = state.quests[qid]
        if quest["suit"] == suit and all(
            _ready_count(state, item) >= quest["items"].count(item)
            for item in set(quest["items"])
        ):
            result.append(qid)
    return result


def _battle_clearings(state: GameState) -> list[int]:
    loc = state.vagabond.location
    return [loc] if loc not in (None, 0) and _battle_targets(state, loc) else []


def _battle_targets(state: GameState, clearing_id: int) -> list[Faction]:
    return _piece_factions_at_location(state, clearing_id)


def _special_actions(state: GameState) -> list[VagabondSpecial]:
    if state.vagabond.character == "thief":
        return [
            VagabondSpecial(f)
            for f in _piece_factions_at_location(state)
            if state.faction_state(f).hand
        ]
    if state.vagabond.character in ("tinker", "ranger"):
        return [VagabondSpecial()]
    return []


def _piece_factions_at_location(
    state: GameState, clearing_id: int | None = None
) -> list[Faction]:
    loc = state.vagabond.location if clearing_id is None else clearing_id
    if loc in (None, 0):
        return []
    return [
        f
        for f in Faction
        if f != Faction.VAGABOND and _faction_has_piece(state, loc, f)
    ]


def _faction_has_piece(state: GameState, clearing_id: int, faction: Faction) -> bool:
    return (
        state.board.warriors[clearing_id][faction] > 0
        or bool(state.board.buildings[clearing_id][faction])
        or bool(state.board.tokens[clearing_id][faction])
    )


def _require_clearing_location(state: GameState) -> int:
    if state.vagabond.location in (None, 0):
        raise ValueError("Vagabond must be in a clearing")
    return state.vagabond.location


def _ready_items(state: GameState) -> dict[ItemType, int]:
    items = dict(state.vagabond.satchel)
    for item, count in state.vagabond.tracks.items():
        items[item] = items.get(item, 0) + count
    return items


def _ready_count(state: GameState, item: ItemType) -> int:
    return _ready_items(state).get(item, 0)


def _undamaged_total(state: GameState, item: ItemType) -> int:
    return (
        _ready_count(state, item)
        + state.vagabond.exhausted_items.get(item, 0)
        + state.vagabond.exhausted_tracks.get(item, 0)
    )


def _exhaust(state: GameState, item: ItemType, count: int) -> None:
    for _ in range(count):
        if state.vagabond.satchel.get(item, 0) > 0:
            _move_count(state.vagabond.satchel, item, -1)
            _move_count(state.vagabond.exhausted_items, item, 1)
        elif state.vagabond.tracks.get(item, 0) > 0:
            _move_count(state.vagabond.tracks, item, -1)
            _move_count(state.vagabond.exhausted_tracks, item, 1)
        else:
            raise ValueError(f"No ready {item.value} to exhaust")


def _gain_item(state: GameState, item: ItemType) -> None:
    pool = (
        state.vagabond.tracks
        if item in TRACK_ITEMS and state.vagabond.tracks.get(item, 0) < 3
        else state.vagabond.satchel
    )
    _move_count(pool, item, 1)


def _damage_one_item(state: GameState) -> None:
    for pool in (
        state.vagabond.satchel,
        state.vagabond.tracks,
        state.vagabond.exhausted_items,
        state.vagabond.exhausted_tracks,
    ):
        for item, count in list(pool.items()):
            if count > 0:
                _move_count(pool, item, -1)
                _move_count(state.vagabond.damaged_items, item, 1)
                return


def _move_count(pool: dict[ItemType, int], item: ItemType, delta: int) -> None:
    pool[item] = pool.get(item, 0) + delta
    if pool[item] <= 0:
        pool.pop(item, None)


def _improve_relationship_from_aid(state: GameState, faction: Faction) -> None:
    relation = state.vagabond.relationships.get(faction, VagabondRelation.INDIFFERENT)
    if relation == VagabondRelation.HOSTILE:
        return
    if relation == VagabondRelation.FRIENDLY:
        state.scores[Faction.VAGABOND] += 2
        return
    state.vagabond.aid_given_this_turn[faction] = (
        state.vagabond.aid_given_this_turn.get(faction, 0) + 1
    )
    needed, next_relation, points = AID_THRESHOLDS[relation]
    if state.vagabond.aid_given_this_turn[faction] >= needed:
        state.vagabond.relationships[faction] = next_relation
        state.vagabond.aid_given_this_turn[faction] = 0
        state.scores[Faction.VAGABOND] += points


def _removed_piece(
    state: GameState,
    faction: Faction,
    *,
    in_battle: bool,
    warrior: bool,
    score_infamy: bool = True,
) -> None:
    if (
        warrior
        and state.vagabond.relationships.get(faction) != VagabondRelation.HOSTILE
    ):
        state.vagabond.relationships[faction] = VagabondRelation.HOSTILE
        return
    if (
        in_battle
        and score_infamy
        and state.vagabond.relationships.get(faction) == VagabondRelation.HOSTILE
    ):
        state.scores[Faction.VAGABOND] += 1


def _has_hostile_warrior(state: GameState, clearing_id: int) -> bool:
    return any(
        state.vagabond.relationships.get(f) == VagabondRelation.HOSTILE
        and state.board.warriors[clearing_id][f] > 0
        for f in Faction
        if f != Faction.VAGABOND
    )


def _defender_piece_count(state: GameState, clearing_id: int, faction: Faction) -> int:
    return (
        state.board.warriors[clearing_id][faction]
        + len(state.board.tokens[clearing_id][faction])
        + len(state.board.buildings[clearing_id][faction])
    )


def _legal_craft_cards(state: GameState) -> list[int]:
    loc = state.vagabond.location
    if loc in (None, 0):
        return []
    clearing_suit = state.board.clearings[loc].suit
    hammers = _ready_count(state, ItemType.HAMMER)
    result = []
    for card_id in state.vagabond.hand:
        card = state.cards[card_id]
        if not card.craftable:
            continue
        if card.craft_cost_any and hammers >= card.craft_cost_any:
            result.append(card_id)
            continue
        if (
            set(card.craft_cost).issubset({clearing_suit})
            and sum(card.craft_cost.values()) <= hammers
        ):
            result.append(card_id)
    return result


def _item_from_card_name(name: str) -> ItemType:
    lowered = name.lower()
    if "tea" in lowered or "sale" in lowered:
        return ItemType.TEAPOT
    if "coin" in lowered or "investments" in lowered or "racket" in lowered:
        return ItemType.COIN
    if "knapsack" in lowered or "bindle" in lowered or "sack" in lowered:
        return ItemType.BAG
    if (
        "boot" in lowered
        or "runner" in lowered
        or "gear" in lowered
        or "visit" in lowered
        or "trail" in lowered
    ):
        return ItemType.BOOT
    if "crossbow" in lowered:
        return ItemType.CROSSBOW
    if "sword" in lowered or "steel" in lowered or "arms" in lowered:
        return ItemType.SWORD
    if "anvil" in lowered:
        return ItemType.HAMMER
    return ItemType.TEAPOT


def _draw_cards(state: GameState, hand: list[int], count: int) -> None:
    for _ in range(count):
        if not state.draw_pile:
            if not state.discard_pile:
                return
            state.draw_pile = list(state.discard_pile)
            state.discard_pile.clear()
        hand.append(state.draw_pile.pop())
