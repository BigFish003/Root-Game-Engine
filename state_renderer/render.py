from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from PIL import Image, ImageDraw, ImageFont


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

        def add_build_spots(center: tuple[int, int], slots: int) -> None:
            cx, cy = center
            rect_w = 14
            rect_h = 9
            spacing = 4
            total_width = slots * rect_w + (slots - 1) * spacing
            start_x = cx - total_width / 2
            y = cy + 20

            for slot_index in range(slots):
                left = start_x + slot_index * (rect_w + spacing)
                draw.rectangle(
                    (left, y, left + rect_w, y + rect_h),
                    fill=(139, 90, 43),
                    outline="black",
                    width=1,
                )

        state_dictionary = self.build_state_dictionary(observation)

        img = Image.new("RGB", (800, 600), color="white")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        # map
        draw.rectangle((0, 0, 550, 350), fill=(85, 107, 85), outline="black", width=3)

        clearing_positions: dict[int, tuple[int, int]] = {
            1: (90, 45),
            2: (270, 45),
            3: (450, 82),
            4: (90, 140),
            5: (240, 120),
            6: (180, 195),
            7: (330, 170),
            8: (450, 195),
            9: (90, 290),
            10: (215, 300),
            11: (330, 270),
            12: (480, 300),
        }
        radius = 28

        # Draw paths first so clearings appear on top of paths.
        drawn_edges: set[tuple[int, int]] = set()
        clearings = state_dictionary.get("clearings", {})
        for clearing_id_str, clearing_data in clearings.items():
            clearing_id = int(clearing_id_str)
            for adjacent in clearing_data.get("adjacent_clearings", []):
                edge = tuple(sorted((clearing_id, adjacent)))
                if edge in drawn_edges:
                    continue
                start = clearing_positions.get(edge[0])
                end = clearing_positions.get(edge[1])
                if start is None or end is None:
                    continue
                draw.line((start, end), fill=(210, 180, 140), width=8)
                drawn_edges.add(edge)

        # Draw clearing circles, ID labels, and build spots.
        for clearing_id_str, clearing_data in clearings.items():
            clearing_id = int(clearing_id_str)
            center = clearing_positions.get(clearing_id)
            if center is None:
                continue

            cx, cy = center
            circle = (cx - radius, cy - radius, cx + radius, cy + radius)
            draw.ellipse(circle, fill=(223, 223, 223), outline="black", width=3)

            label = str(clearing_id)
            label_bbox = draw.textbbox((0, 0), label, font=font)
            label_w = label_bbox[2] - label_bbox[0]
            label_h = label_bbox[3] - label_bbox[1]
            draw.text((cx - label_w / 2, cy - label_h / 2), label, fill="black", font=font)

            slots = int(clearing_data.get("building_slots", 0))
            print(slots)
            if slots > 0:
                add_build_spots(center, slots)

        #faction boards
        #marquise
        draw.rectangle((0,350,200,600), fill=(229,182,88), outline="black", width=3)

        #eryie
        draw.rectangle((200,350,400,600), fill=(46,117,179), outline="black", width=3)

        #woodland
        draw.rectangle((400,350,600,600), fill=(53,101,40), outline="black", width=3)

        #vagabound
        draw.rectangle((600,350,800,600), fill=(111,111,111), outline="black", width=3)


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
