"""Convert Root_June dataset rows into RootEngine instances.

The mod currently stores JSONL event rows.  ``turn_end`` rows contain one
captured end state under ``end_states[0].end_state``; ``game_end`` rows are
summary-only and cannot be converted to a board state.  Older
``ai_decisions_*.jsonl`` rows with a top-level ``gameState`` object are still
accepted.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from root_engine.cards import create_base_deck
from root_engine.engine import RootEngine
from root_engine.enums import BuildingType, DecisionType, Faction, Phase, Suit, TokenType
from root_engine.map_data import create_base_forests, create_base_map
from root_engine.models import BoardState, DecisionContext, GameState
from root_engine.state import create_initial_state


_FACTION_ALIASES: dict[str, Faction] = {
    "marquise": Faction.MARQUISE,
    "marquisedecat": Faction.MARQUISE,
    "mechanicalmarquise": Faction.MARQUISE,
    "eyrie": Faction.EYRIE,
    "eyriedynasties": Faction.EYRIE,
    "electriceyrie": Faction.EYRIE,
    "alliance": Faction.ALLIANCE,
    "woodlandalliance": Faction.ALLIANCE,
    "automatedalliance": Faction.ALLIANCE,
    "vagabond": Faction.VAGABOND,
    "secondvagabond": Faction.VAGABOND,
    "vagabot": Faction.VAGABOND,
}

_BUILDING_ALIASES: dict[str, BuildingType] = {
    "sawmill": BuildingType.SAWMILL,
    "workshop": BuildingType.WORKSHOP,
    "recruiter": BuildingType.RECRUITER,
    "roost": BuildingType.ROOST,
    "base": BuildingType.BASE,
    "foxbase": BuildingType.BASE,
    "rabbitbase": BuildingType.BASE,
    "mousebase": BuildingType.BASE,
}

_TOKEN_ALIASES: dict[str, TokenType] = {
    "wood": TokenType.WOOD,
    "keep": TokenType.KEEP,
    "sympathy": TokenType.SYMPATHY,
}

_SUIT_ALIASES: dict[str, Suit] = {
    "fox": Suit.FOX,
    "foxes": Suit.FOX,
    "rabbit": Suit.RABBIT,
    "rabbits": Suit.RABBIT,
    "mouse": Suit.MOUSE,
    "mice": Suit.MOUSE,
    "bird": Suit.BIRD,
}

_PHASE_BY_INDEX: dict[int, Phase] = {
    0: Phase.BIRDSONG,
    1: Phase.DAYLIGHT,
    2: Phase.EVENING,
}

_EYRIE_DECREE_COLUMNS = ("recruit", "move", "battle", "build")
_EYRIE_VIZIER_BY_COLUMN = {
    "recruit": -101,
    "move": -102,
    "battle": -103,
    "build": -104,
}

# Root_June now writes root_engine clearing ids (1-12).  Keep this hook small
# and explicit so old/manual remaps can still be applied in one place if needed.
_UNITY_CLEARING_TO_ENGINE_CLEARING: dict[int, int] = {
    1: 1,
    2: 2,
    3: 3,
    4: 5,
    5: 4,
    6: 6,
    7: 7,
    8: 8,
    9: 12,
    10: 11,
    11: 10,
    12: 9,
}


def gamestate_line_to_root_engine(gamestate_line: str | Mapping[str, Any]) -> RootEngine:
    """Build a ``RootEngine`` from one mod dataset line.

    ``gamestate_line`` may be:
    - a JSONL ``turn_end`` row from ``turn_end_games_*.jsonl``;
    - a JSONL row from older ``ai_decisions_*.jsonl`` files;
    - a JSON string containing the nested ``gameState`` object;
    - a JSON string containing the nested ``end_state`` object;
    - an already parsed dict for either of those shapes.

    The returned engine has ``engine.get_state()`` set to the converted state.
    """

    state = gamestate_line_to_state(gamestate_line)
    excluded = {faction for faction in Faction if faction not in state.turn.turn_order}
    engine = RootEngine(seed=state.seed, excluded_factions=excluded)
    engine._state = state
    return engine


def game_state_line_to_root_engine(gamestate_line: str | Mapping[str, Any]) -> RootEngine:
    """Alias for callers that prefer ``game_state`` spelling."""

    return gamestate_line_to_root_engine(gamestate_line)


def gamestate_to_root_engine(gamestate: str | Mapping[str, Any]) -> RootEngine:
    """Alias for converting a parsed/nested game state object."""

    return gamestate_line_to_root_engine(gamestate)


def convert_gamestate_line(gamestate_line: str | Mapping[str, Any]) -> RootEngine:
    """Friendly alias: convert one dataset row into a ``RootEngine``."""

    return gamestate_line_to_root_engine(gamestate_line)


def convert_gamestate_line_to_root_engine(gamestate_line: str | Mapping[str, Any]) -> RootEngine:
    """Friendly alias: convert one dataset row into a ``RootEngine``."""

    return gamestate_line_to_root_engine(gamestate_line)


def gamestate_line_to_state(gamestate_line: str | Mapping[str, Any]) -> GameState:
    """Build a ``GameState`` from one mod dataset line or gameState dict."""

    payload = _parse_payload(gamestate_line)
    game_state = _extract_game_state(payload)

    factions = _active_factions(game_state)
    excluded = {faction for faction in Faction if faction not in factions}
    state = create_initial_state(seed=None, excluded_factions=excluded)

    _reset_board(state)
    _apply_board(state, game_state)
    card_allocator = _new_card_allocator()
    _apply_players(state, game_state, card_allocator)
    _apply_eyrie_decree(state, game_state, card_allocator)
    _apply_table_cards(state, game_state, card_allocator)
    _apply_turn_and_decision(state, game_state)
    _recompute_supplies(state)
    return state


def _parse_payload(value: str | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if not isinstance(value, str):
        raise TypeError(f"Expected JSON string or mapping, got {type(value)!r}")
    text = value.strip()
    if not text:
        raise ValueError("Cannot convert an empty gamestate line")
    parsed = json.loads(text)
    if not isinstance(parsed, Mapping):
        raise ValueError("Gamestate line must decode to a JSON object")
    return parsed


def _extract_game_state(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    row_type = _get(payload, "row_type") or _get(payload, "rowType")
    if row_type == "game_end":
        raise ValueError("game_end rows are summaries and do not contain an end_state")

    game_state = _get(payload, "gameState")
    if isinstance(game_state, Mapping):
        return game_state

    end_state = _get(payload, "end_state")
    if isinstance(end_state, Mapping):
        return end_state

    end_states = _list(_get(payload, "end_states") or _get(payload, "endStates"))
    if end_states:
        first = end_states[0]
        if isinstance(first, Mapping):
            nested = _get(first, "end_state") or _get(first, "endState")
            if isinstance(nested, Mapping):
                return nested
            if _looks_like_game_state(first):
                return first

    if _looks_like_game_state(payload):
        return payload

    raise ValueError("Dataset row does not contain a convertible gameState/end_state object")


def iter_turn_end_states(lines: Any) -> list[GameState]:
    """Convert all ``turn_end`` rows from an iterable of JSONL lines.

    Summary ``game_end`` rows are skipped.  This is handy for reading a whole
    ``turn_end_games_*.jsonl`` file into per-turn RootEngine states.
    """

    states: list[GameState] = []
    for line in lines:
        payload = _parse_payload(line)
        if (_get(payload, "row_type") or _get(payload, "rowType")) == "game_end":
            continue
        states.append(gamestate_line_to_state(payload))
    return states


def iter_turn_end_engines(lines: Any) -> list[RootEngine]:
    """Convert all ``turn_end`` rows from an iterable of JSONL lines."""

    engines: list[RootEngine] = []
    for state in iter_turn_end_states(lines):
        excluded = {faction for faction in Faction if faction not in state.turn.turn_order}
        engine = RootEngine(seed=state.seed, excluded_factions=excluded)
        engine._state = state
        engines.append(engine)
    return engines


def _looks_like_game_state(value: Mapping[str, Any]) -> bool:
    return isinstance(_get(value, "players"), list) or isinstance(_get(value, "board"), Mapping)


def _active_factions(game_state: Mapping[str, Any]) -> list[Faction]:
    factions: list[Faction] = []
    for player in _list(_get(game_state, "players")):
        faction = _faction(_get(player, "faction"))
        if faction is not None and faction not in factions:
            factions.append(faction)

    turn_order = []
    for name in _list(_get(_get(game_state, "match"), "factionSetupOrder")):
        faction = _faction(name)
        if faction is not None and faction not in turn_order:
            turn_order.append(faction)

    return factions or turn_order or list(Faction)


def _reset_board(state: GameState) -> None:
    state.board = BoardState(
        clearings=create_base_map(),
        forests=create_base_forests(),
        warriors={cid: {faction: 0 for faction in Faction} for cid in state.board.clearings},
        buildings={cid: {faction: [] for faction in Faction} for cid in state.board.clearings},
        tokens={cid: {faction: [] for faction in Faction} for cid in state.board.clearings},
        ruin_items={},
    )


def _apply_board(state: GameState, game_state: Mapping[str, Any]) -> None:
    board = _get(game_state, "board")
    for clearing in _list(_get(board, "clearings")):
        clearing_id = _remap_clearing_id(_int(_get(clearing, "clearingId")))
        if clearing_id not in state.board.clearings:
            continue

        _apply_clearing_metadata(state, clearing_id, clearing)
        _apply_piece_counts(state, clearing_id, clearing)
        _apply_piece_groups(state, clearing_id, clearing)
        _apply_piece_flags(state, clearing_id, clearing)


def _apply_clearing_metadata(state: GameState, clearing_id: int, clearing: Mapping[str, Any]) -> None:
    model = state.board.clearings[clearing_id]
    suit = _suit(_get(clearing, "suit"))
    if suit is not None:
        model.suit = suit

    slots = _int(_get(clearing, "buildingSlots"), default=model.building_slots)
    if slots > 0:
        model.building_slots = slots

    adjacent = [_remap_clearing_id(_int(value)) for value in _list(_get(clearing, "adjacentClearings"))]
    adjacent = [value for value in adjacent if value in state.board.clearings]
    if adjacent:
        model.adjacent_clearings = adjacent

    model.has_ruin = bool(_get(clearing, "hasRuin", model.has_ruin))


def _apply_piece_counts(state: GameState, clearing_id: int, clearing: Mapping[str, Any]) -> None:
    pieces_by_faction = _get(clearing, "piecesByFaction") or {}
    if not isinstance(pieces_by_faction, Mapping):
        return

    for faction_name, piece_info in pieces_by_faction.items():
        faction = _faction(faction_name)
        counts = _get(piece_info, "counts") if isinstance(piece_info, Mapping) else None
        if faction is None or not isinstance(counts, Mapping):
            continue

        warriors = _int(_get(counts, "warrior"))
        if warriors:
            state.board.warriors[clearing_id][faction] = warriors


def _apply_piece_groups(state: GameState, clearing_id: int, clearing: Mapping[str, Any]) -> None:
    for group in _list(_get(clearing, "pieces")) + _list(_get(clearing, "allPieces")):
        owner = _faction(_get(group, "ownerFaction"))
        if owner is None:
            owner = _faction(_get(_get(group, "owner"), "faction"))

        name = _piece_identity(group)
        count = max(1, _int(_get(group, "count"), default=1))
        if owner is None or not name:
            continue

        if owner == Faction.VAGABOND and "vagabond" in _norm(name):
            state.vagabond.location = clearing_id
            state.vagabond.forest_location = None
            continue

        building = _building_type(name)
        if building is not None:
            state.board.buildings[clearing_id][owner].extend([building] * count)
            continue

        token = _token_type(name)
        if token is not None:
            state.board.tokens[clearing_id][owner].extend([token] * count)


def _apply_piece_flags(state: GameState, clearing_id: int, clearing: Mapping[str, Any]) -> None:
    if _bool(_get(clearing, "hasKeep")):
        _ensure_token(state, clearing_id, Faction.MARQUISE, TokenType.KEEP)
        state.marquise.keep_clearing = clearing_id
    if _bool(_get(clearing, "hasSympathy")):
        _ensure_token(state, clearing_id, Faction.ALLIANCE, TokenType.SYMPATHY)
    if _bool(_get(clearing, "hasRoost")):
        _ensure_building(state, clearing_id, Faction.EYRIE, BuildingType.ROOST)


def _apply_players(
    state: GameState,
    game_state: Mapping[str, Any],
    card_allocator: dict[tuple[str, Suit | None], deque[int]],
) -> None:
    for player in _list(_get(game_state, "players")):
        faction = _faction(_get(player, "faction"))
        if faction is None:
            continue

        hand_ids = _cards_from_area(_get(player, "hand"), card_allocator)
        if faction == Faction.MARQUISE:
            state.marquise.hand = hand_ids
            state.scores[faction] = _player_score(player)
        elif faction == Faction.EYRIE:
            state.eyrie.hand = hand_ids
            leader = _leader_name(_get(player, "eyrieLeader"))
            if leader is not None:
                state.eyrie.leader = leader
            state.scores[faction] = _player_score(player)
        elif faction == Faction.ALLIANCE:
            state.alliance.hand = hand_ids
            state.scores[faction] = _player_score(player)
        elif faction == Faction.VAGABOND:
            state.vagabond.hand = hand_ids
            state.scores[faction] = _player_score(player)
            location = _remap_clearing_id(_int(_get(player, "currentTurnLocation"), default=0))
            if location in state.board.clearings:
                state.vagabond.location = location


def _apply_eyrie_decree(
    state: GameState,
    game_state: Mapping[str, Any],
    card_allocator: dict[tuple[str, Suit | None], deque[int]],
) -> None:
    eyrie_player = None
    for player in _list(_get(game_state, "players")):
        if _faction(_get(player, "faction")) == Faction.EYRIE:
            eyrie_player = player
            break

    if not isinstance(eyrie_player, Mapping):
        return

    decree = _get(eyrie_player, "eyrieDecree") or _get(eyrie_player, "eyrie_decree")
    if not isinstance(decree, Mapping):
        return

    converted = {column: [] for column in _EYRIE_DECREE_COLUMNS}
    for column in _EYRIE_DECREE_COLUMNS:
        converted[column] = _cards_from_decree_area(_get(decree, column), column, card_allocator)

    if any(converted.values()):
        state.eyrie.decree = converted
        state.eyrie.decree_cards_remaining = {column: list(cards) for column, cards in converted.items()}


def _apply_table_cards(
    state: GameState,
    game_state: Mapping[str, Any],
    card_allocator: dict[tuple[str, Suit | None], deque[int]],
) -> None:
    table = _get(game_state, "table")
    draw_pile = _cards_from_area(_get(table, "drawPile") or _get(table, "draw_pile"), card_allocator)
    discard_pile = _cards_from_area(_get(table, "discardPile") or _get(table, "discard_pile"), card_allocator)

    used = set(draw_pile) | set(discard_pile)
    for faction in Faction:
        used.update(state.faction_state(faction).hand)
    for cards in state.eyrie.decree.values():
        used.update(card_id for card_id in cards if card_id > 0)

    if draw_pile:
        state.draw_pile = draw_pile + [card_id for card_id in state.cards if card_id not in used]
    else:
        state.draw_pile = [card_id for card_id in state.cards if card_id not in used]
    state.discard_pile = discard_pile


def _apply_turn_and_decision(state: GameState, game_state: Mapping[str, Any]) -> None:
    turn = _get(game_state, "turn")
    current = _faction(
        _get(turn, "currentFaction")
        or _get(turn, "activeFaction")
        or _get(turn, "selectingFaction")
    )
    if current is not None:
        state.turn.current_faction = current

    active = _active_factions(game_state)
    state.turn.turn_order = active

    turn_number = _int(_get(turn, "turnNumber"), default=0)
    state.turn.round_number = max(1, (turn_number // max(1, len(active))) + 1)

    phase = _phase_from_player(game_state, state.turn.current_faction)
    if phase is not None:
        state.turn.phase = phase

    state.decision_context = DecisionContext(decision_type=DecisionType.MAIN_ACTION)


def _recompute_supplies(state: GameState) -> None:
    state.marquise.warriors_in_supply = max(
        0, 25 - sum(state.board.warriors[cid][Faction.MARQUISE] for cid in state.board.clearings)
    )
    state.eyrie.warriors_in_supply = max(
        0, 20 - sum(state.board.warriors[cid][Faction.EYRIE] for cid in state.board.clearings)
    )
    state.alliance.sympathy_in_supply = max(
        0,
        10
        - sum(
            1
            for cid in state.board.clearings
            for token in state.board.tokens[cid][Faction.ALLIANCE]
            if token == TokenType.SYMPATHY
        ),
    )

    state.marquise.buildings_in_supply = {
        BuildingType.SAWMILL: max(0, 6 - _count_buildings(state, Faction.MARQUISE, BuildingType.SAWMILL)),
        BuildingType.WORKSHOP: max(0, 6 - _count_buildings(state, Faction.MARQUISE, BuildingType.WORKSHOP)),
        BuildingType.RECRUITER: max(0, 6 - _count_buildings(state, Faction.MARQUISE, BuildingType.RECRUITER)),
    }
    state.eyrie.roosts_in_supply = max(0, 7 - _count_buildings(state, Faction.EYRIE, BuildingType.ROOST))
    state.alliance.bases = {
        suit: any(
            BuildingType.BASE in state.board.buildings[cid][Faction.ALLIANCE]
            and state.board.clearings[cid].suit == suit
            for cid in state.board.clearings
        )
        for suit in (Suit.FOX, Suit.RABBIT, Suit.MOUSE)
    }


def _cards_from_area(
    area: Any,
    card_allocator: dict[tuple[str, Suit | None], deque[int]],
) -> list[int]:
    card_ids: list[int] = []
    for entity in _list(_get(area, "entities")):
        card_id = _card_id_from_entity(entity, card_allocator)
        if card_id is not None:
            card_ids.append(card_id)
    return card_ids


def _cards_from_decree_area(
    area: Any,
    column: str,
    card_allocator: dict[tuple[str, Suit | None], deque[int]],
) -> list[int]:
    card_ids: list[int] = []
    for entity in _list(_get(area, "entities")):
        card_id = _card_id_from_decree_entity(entity, column, card_allocator)
        if card_id is not None:
            card_ids.append(card_id)
    return card_ids


def _card_id_from_decree_entity(
    entity: Mapping[str, Any],
    column: str,
    card_allocator: dict[tuple[str, Suit | None], deque[int]],
) -> int | None:
    identity = _piece_identity(entity)
    if "vizier" in _norm(identity):
        return _EYRIE_VIZIER_BY_COLUMN[column]
    return _card_id_from_entity(entity, card_allocator)


def _card_id_from_entity(
    entity: Mapping[str, Any],
    card_allocator: dict[tuple[str, Suit | None], deque[int]],
) -> int | None:
    identity = _piece_identity(entity)
    if not identity:
        return None

    key = _card_key_from_identity(identity)
    if key is None:
        return None

    source_suit = _suit(_get(entity, "suit"))
    if source_suit is not None:
        suited_key = (key[0], source_suit)
        queue = card_allocator.get(suited_key)
        if queue:
            return queue.popleft()

    queue = card_allocator.get(key)
    if queue:
        return queue.popleft()

    # Fall back by card name if suit parsing failed or the source name differs.
    name_only = key[0]
    for candidate_key, candidate_ids in card_allocator.items():
        if candidate_key[0] == name_only and candidate_ids:
            return candidate_ids.popleft()
    return None


def _new_card_allocator() -> dict[tuple[str, Suit | None], deque[int]]:
    index: dict[tuple[str, Suit | None], deque[int]] = defaultdict(deque)
    for card in create_base_deck():
        index[(_norm(card.name), card.suit)].append(card.card_id)
    return index


def _card_key_from_identity(identity: str) -> tuple[str, Suit | None] | None:
    value = _strip_card_suffix(identity)
    suit = None
    for suffix, parsed_suit in (
        ("foxes", Suit.FOX),
        ("fox", Suit.FOX),
        ("rabbits", Suit.RABBIT),
        ("rabbit", Suit.RABBIT),
        ("mice", Suit.MOUSE),
        ("mouse", Suit.MOUSE),
        ("bird", Suit.BIRD),
    ):
        if value.endswith(suffix):
            suit = parsed_suit
            value = value[: -len(suffix)]
            break

    if not value:
        return None
    return value, suit


def _leader_name(value: Any) -> str | None:
    normalized = _norm(value)
    for leader in ("despot", "commander", "charismatic", "builder"):
        if leader in normalized:
            return leader
    return None


def _strip_card_suffix(identity: str) -> str:
    value = _norm(identity)
    for suffix in ("card", "archetype"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
    return value


def _piece_identity(piece: Mapping[str, Any]) -> str:
    archetype = str(_get(piece, "archetype") or "")
    archetype_type = str(_get(piece, "archetypeType") or "")
    name = str(_get(piece, "name") or "")
    if archetype_type:
        return archetype_type
    if archetype and _norm(archetype) not in {"archetype", "cardarchetype"}:
        return archetype
    return name


def _phase_from_player(game_state: Mapping[str, Any], current: Faction) -> Phase | None:
    for player in _list(_get(game_state, "players")):
        if _faction(_get(player, "faction")) == current:
            phase_index = _int(_get(player, "gamePhase"), default=-1)
            return _PHASE_BY_INDEX.get(phase_index)
    return None


def _player_score(player: Mapping[str, Any]) -> int:
    score = _get(player, "score")
    if score is not None:
        return _int(score)
    return _int(_get(player, "scoreFromPointSources"))


def _count_buildings(state: GameState, faction: Faction, building: BuildingType) -> int:
    return sum(
        1
        for cid in state.board.clearings
        for placed in state.board.buildings[cid][faction]
        if placed == building
    )


def _ensure_building(state: GameState, clearing_id: int, faction: Faction, building: BuildingType) -> None:
    if building not in state.board.buildings[clearing_id][faction]:
        state.board.buildings[clearing_id][faction].append(building)


def _ensure_token(state: GameState, clearing_id: int, faction: Faction, token: TokenType) -> None:
    if token not in state.board.tokens[clearing_id][faction]:
        state.board.tokens[clearing_id][faction].append(token)


def _remap_clearing_id(clearing_id: int) -> int:
    return _UNITY_CLEARING_TO_ENGINE_CLEARING.get(clearing_id, clearing_id)


def _building_type(value: Any) -> BuildingType | None:
    return _BUILDING_ALIASES.get(_norm(value))


def _token_type(value: Any) -> TokenType | None:
    return _TOKEN_ALIASES.get(_norm(value))


def _faction(value: Any) -> Faction | None:
    if isinstance(value, Faction):
        return value
    return _FACTION_ALIASES.get(_norm(value))


def _suit(value: Any) -> Suit | None:
    if isinstance(value, Suit):
        return value
    return _SUIT_ALIASES.get(_norm(value))


def _get(value: Any, key: str, default: Any = None) -> Any:
    if not isinstance(value, Mapping):
        return default
    if key in value:
        return value[key]
    snake = _camel_to_snake(key)
    if snake in value:
        return value[snake]
    return default


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _norm(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).split(".")[-1]
    text = text.replace("_", "")
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _camel_to_snake(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
