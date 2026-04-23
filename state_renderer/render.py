from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from PIL import Image, ImageDraw, ImageFont


class state_renderer:


    """Helpers for rendering and inspecting Root game states."""
    def render_board(self, observation: Any, output_path: str) -> None:
        """Render the game board as an image.

        The renderer currently draws a placeholder board and creates a
        state dictionary for easier future rendering development.
        """

        def make_marquise_piece(x, y):
            width, height, orange = 18, 30, (255, 128, 0)
            ear_base_y = y + height // 3
            draw.rectangle((x, ear_base_y, x + width, y + height), fill=orange)
            draw.polygon([(x + width // 3, y), (x, ear_base_y), (x + width // 2, ear_base_y)], fill=orange)
            draw.polygon([(x + 2 * width // 3, y), (x + width // 2, ear_base_y), (x + width, ear_base_y)], fill=orange)
            draw.line([(x, y + height), (x, ear_base_y), (x + width // 3, y), (x + width // 2, ear_base_y),(x + 2 * width // 3, y), (x + width, ear_base_y), (x + width, y + height), (x, y + height)], fill="black", width=1)
            r, eye_y = 1, y + height * 0.57
            for ex in (x + width * 0.35, x + width * 0.65):
                draw.ellipse((ex - r, eye_y - r, ex + r, eye_y + r), fill="black")

        def add_build_spots(center: tuple[int, int], slots: int) -> None:
            cx, cy = center
            square_size = 20
            half_size = square_size / 2
            spacing = 4
            slots_to_draw = min(slots, 3)
            total_width = slots_to_draw * square_size + (slots_to_draw - 1) * spacing
            start_x = cx - total_width / 2 + half_size
            slot_center_y = cy - radius * 0.45

            for slot_index in range(slots_to_draw):
                slot_center_x = start_x + slot_index * (square_size + spacing)
                left = slot_center_x - half_size
                top = slot_center_y - half_size
                draw.rectangle(
                    (left, top, left + square_size, top + square_size),
                    fill=None,
                    outline="black",
                    width=1,
                )

        def add_marquise_supply_tiles(inner_rect: tuple[int, int, int, int]) -> None:
            left, top, right, bottom = inner_rect
            faction_data = state_dictionary.get("factions", {}).get("marquise", {}).get("public_data", {})
            buildings = faction_data.get("buildings_in_supply", {})
            rows = [
                ("Workshop", int(buildings.get("workshop", 0)), Workshop),
                ("Sawmill", int(buildings.get("sawmill", 0)), Sawmill),
                ("Recruiter", int(buildings.get("recruiter", 0)), Recruiter),
            ]

            row_height = (bottom - top) // len(rows)
            slot_size = 18
            slot_spacing = 4
            slots_per_row = 6
            slots_width = slots_per_row * slot_size + (slots_per_row - 1) * slot_spacing
            slots_start_x = right - 8 - slots_width

            for idx, (label, remaining, piece_image) in enumerate(rows):
                row_top = top + idx * row_height
                row_center_y = row_top + row_height // 2
                draw.text((left + 8, row_center_y - 6), label, fill="black", font=font)

                tile_y = row_center_y - slot_size // 2
                for slot_idx in range(slots_per_row):
                    tile_x = slots_start_x + slot_idx * (slot_size + slot_spacing)
                    draw.rectangle(
                        (tile_x, tile_y, tile_x + slot_size, tile_y + slot_size),
                        fill=None,
                        outline="black",
                        width=1,
                    )
                    if slot_idx < remaining:
                        piece_x = tile_x + (slot_size - piece_image.width) // 2
                        piece_y = tile_y + (slot_size - piece_image.height) // 2
                        img.paste(piece_image, (piece_x, piece_y), piece_image)

        state_dictionary = self.build_state_dictionary(observation)

        img = Image.new("RGB", (800, 600), color="white")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        #piece images ex: img.paste(Workshop, (50, 50), Workshop)
        Workshop = Image.open("state_renderer/images/anvil_piece.png").convert("RGBA")
        Workshop = Workshop.resize((16, 16))
        Sawmill = Image.open("state_renderer/images/Sawmill.webp").convert("RGBA")
        Sawmill = Sawmill.resize((16, 16))
        Recruiter = Image.open("state_renderer/images/Recruiter.webp").convert("RGBA")
        Recruiter = Recruiter.resize((16, 16))

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
        radius = 45

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
            if slots > 0:
                add_build_spots(center, slots)

        #faction boards
        #marquise
        draw.rectangle((0,350,200,600), fill=(229,182,88), outline="black", width=3)
        marquise_inner_rect = (10, 450, 190, 590)
        draw.rectangle(marquise_inner_rect, fill=(223, 194, 134), outline="black", width=3)
        add_marquise_supply_tiles(marquise_inner_rect)

        #eryie
        draw.rectangle((200,350,400,600), fill=(46,117,179), outline="black", width=3)

        #woodland
        draw.rectangle((400,350,600,600), fill=(53,101,40), outline="black", width=3)

        #vagabound
        draw.rectangle((600,350,800,600), fill=(111,111,111), outline="black", width=3)


        img.save(output_path)

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
