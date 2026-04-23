from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from PIL import Image, ImageDraw


class state_renderer:
    """Helpers for rendering and inspecting Root game states."""

    def build_state_dictionary(self, state: Any) -> dict[str, Any]:
        """Return an easy-to-read dictionary from a state/observation object.

        The output is intended for renderer development and keeps a stable,
        understandable top-level structure while preserving all nested data.
        """

        raw = self._normalize_value(state)

        if not isinstance(raw, dict):
            return {"value": raw}

        return {
            "meta": {
                "state_type": type(state).__name__,
                "current_faction": raw.get("current_faction"),
                "current_phase": raw.get("current_phase"),
                "observer": raw.get("observer"),
            },
            "turn": raw.get("turn", {}),
            "scores": raw.get("scores", {}),
            "victory_points": raw.get("victory_points", {}),
            "clearings": raw.get("clearings", {}),
            "paths": raw.get("paths", []),
            "factions": raw.get("factions", {}),
            "cards": {
                "deck_count": raw.get("deck_count"),
                "discard_pile": raw.get("discard_pile", []),
            },
            "raw": raw,
        }

    def render_board(self, observation: Any, output_path: str) -> None:
        """Render the game board as an image.

        The renderer currently draws a placeholder board and creates a
        state dictionary for easier future rendering development.
        """

        state_dictionary = self.build_state_dictionary(observation)

        img = Image.new("RGB", (800, 600), color="white")
        draw = ImageDraw.Draw(img)

        draw.rectangle((0, 0, 550, 350), fill="lightgreen", outline="black", width=3)
        draw.text((12, 12), f"State: {state_dictionary['meta']['state_type']}", fill="black")

        img.save(output_path)

    def _normalize_value(self, value: Any) -> Any:
        """Recursively convert dataclasses/enums to Python primitives."""

        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value):
            return self._normalize_value(asdict(value))
        if isinstance(value, dict):
            normalized: dict[str, Any] = {}
            for key, nested_value in value.items():
                normalized[str(self._normalize_value(key))] = self._normalize_value(nested_value)
            return normalized
        if isinstance(value, list):
            return [self._normalize_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._normalize_value(item) for item in value]
        return value


Render = state_renderer()
