"""Core enums used by the Root game engine."""

from __future__ import annotations

from enum import Enum, auto


class Faction(str, Enum):
    """Playable factions in base Root."""

    MARQUISE = "marquise"
    EYRIE = "eyrie"
    ALLIANCE = "alliance"
    VAGABOND = "vagabond"


class Suit(str, Enum):
    """Card/clearing suit."""

    FOX = "fox"
    RABBIT = "rabbit"
    MOUSE = "mouse"
    BIRD = "bird"


class PieceType(str, Enum):
    """Board pieces that can be placed in clearings."""

    WARRIOR = "warrior"
    BUILDING = "building"
    TOKEN = "token"


class BuildingType(str, Enum):
    """Root base-game building categories."""

    SAWMILL = "sawmill"
    WORKSHOP = "workshop"
    RECRUITER = "recruiter"
    ROOST = "roost"
    BASE = "base"


class TokenType(str, Enum):
    """Token categories for base game."""

    WOOD = "wood"
    KEEP = "keep"
    SYMPATHY = "sympathy"


class ItemType(str, Enum):
    """Vagabond items."""

    BOOT = "boot"
    SWORD = "sword"
    TORCH = "torch"
    TEAPOT = "teapot"
    HAMMER = "hammer"
    CROSSBOW = "crossbow"
    COIN = "coin"
    BAG = "bag"


class Phase(str, Enum):
    """Turn phases."""

    BIRDSONG = "birdsong"
    DAYLIGHT = "daylight"
    EVENING = "evening"


class DecisionType(str, Enum):
    """Current atomic decision expected by the engine."""

    MAIN_ACTION = "main_action"
    SELECT_MOVE_SOURCE = "select_move_source"
    SELECT_MOVE_DESTINATION = "select_move_destination"
    SELECT_BATTLE_CLEARING = "select_battle_clearing"
    SELECT_BATTLE_TARGET = "select_battle_target"


class CardTag(str, Enum):
    """Crafting/effect tags for cards."""

    ITEM = "item"
    PERSISTENT_EFFECT = "persistent_effect"
    DOMINANCE = "dominance"
    AMBUSH = "ambush"


class VagabondRelation(str, Enum):
    """Relationship states between Vagabond and other factions."""

    INDIFFERENT = "indifferent"
    AMIABLE = "amiable"
    FRIENDLY = "friendly"
    HOSTILE = "hostile"
