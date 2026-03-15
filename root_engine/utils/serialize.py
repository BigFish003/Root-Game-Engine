"""Serialization helpers for engine state."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


def to_jsonable(value: Any) -> Any:
    """Recursively convert dataclasses/enums to JSON-compatible values."""

    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {to_jsonable(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [to_jsonable(v) for v in value]
    return value
