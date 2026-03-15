"""Deterministic RNG helpers."""

from __future__ import annotations

import random
from typing import Optional


def create_rng(seed: Optional[int]) -> random.Random:
    """Create a local pseudo-random generator."""

    return random.Random(seed)
