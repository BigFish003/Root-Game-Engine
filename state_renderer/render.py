from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from PIL import Image, ImageDraw, ImageFont

try:
    from root_engine.cards import create_base_deck
except ImportError:  # pragma: no cover - keeps direct renderer use working from odd cwd setups.
    create_base_deck = None


class state_renderer:
    """Helpers for rendering and inspecting Root game states."""

    def render_board(self, observation: Any, output_path: str) -> None:
        """Render the game board as an image."""

        def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
            candidates = ["DejaVuSans-Bold.ttf", "Arial Bold.ttf"] if bold else ["DejaVuSans.ttf", "Arial.ttf"]
            for font_name in candidates:
                try:
                    return ImageFont.truetype(font_name, size=size)
                except OSError:
                    continue
            return ImageFont.load_default()

        def make_marquise_piece(x: int, y: int) -> None:
            width, height, orange = 18, 30, (255, 128, 0)
            ear_base_y = y + height // 3
            _draw_warrior_piece(x, y, orange)

        def make_eyrie_piece(x: int, y: int) -> None:
            _draw_warrior_piece(x, y, (72, 135, 201))

        def make_alliance_piece(x: int, y: int) -> None:
            _draw_warrior_piece(x, y, (84, 155, 72))

        def make_vagabond_piece(x: int, y: int) -> None:
            _draw_warrior_piece(x, y, (54, 69, 79))

        def _draw_warrior_piece(x: int, y: int, color: tuple[int, int, int]) -> None:
            width, height = 18, 30
            ear_base_y = y + height // 3
            draw.rectangle((x, ear_base_y, x + width, y + height), fill=color)
            draw.polygon([(x + width // 3, y), (x, ear_base_y), (x + width // 2, ear_base_y)], fill=color)
            draw.polygon([(x + 2 * width // 3, y), (x + width // 2, ear_base_y), (x + width, ear_base_y)], fill=color)
            draw.line(
                [
                    (x, y + height),
                    (x, ear_base_y),
                    (x + width // 3, y),
                    (x + width // 2, ear_base_y),
                    (x + 2 * width // 3, y),
                    (x + width, ear_base_y),
                    (x + width, y + height),
                    (x, y + height),
                ],
                fill="black",
                width=1,
            )
            r, eye_y = 1, y + height * 0.57
            for ex in (x + width * 0.35, x + width * 0.65):
                draw.ellipse((ex - r, eye_y - r, ex + r, eye_y + r), fill="black")

        def add_build_spots(center: tuple[int, int], slots: int, placed_buildings: list[tuple[str, str]]) -> None:
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
                draw.rectangle((left, top, left + square_size, top + square_size), fill=None, outline="black", width=1)
                if slot_index >= len(placed_buildings):
                    continue
                faction, building_name = placed_buildings[slot_index]
                image = building_images.get((faction, building_name))
                if image is None:
                    draw.text((left + 2, top + 5), building_name[:2].upper(), fill="black", font=small_font)
                    continue
                px = int(left + (square_size - image.width) // 2)
                py = int(top + (square_size - image.height) // 2)
                img.paste(image, (px, py), image)

        def place_tokens(center: tuple[int, int], placed_tokens: list[tuple[str, str]]) -> None:
            if not placed_tokens:
                return
            cx, cy = center
            icon_size = 16
            spacing = 3
            total_width = len(placed_tokens) * icon_size + (len(placed_tokens) - 1) * spacing
            start_x = cx - total_width // 2
            top_y = cy - icon_size // 2
            for idx, (faction, token_name) in enumerate(placed_tokens):
                x = int(start_x + idx * (icon_size + spacing))
                image = token_images.get((faction, token_name))
                if image is None:
                    draw.rectangle((x, top_y, x + icon_size, top_y + icon_size), outline="black", fill=(245, 245, 210), width=1)
                    draw.text((x + 2, top_y + 4), token_name[:2].upper(), fill="black", font=small_font)
                    continue
                img.paste(image, (x, top_y), image)

        def place_warriors(center: tuple[int, int], placed_warriors: list[str]) -> None:
            if not placed_warriors:
                return
            cx, cy = center
            piece_width, piece_height = 18, 30
            usable_width = int(radius * 1.55)
            count = len(placed_warriors)
            max_left = cx - usable_width // 2
            step = piece_width if count == 1 else min(piece_width, (usable_width - piece_width) // max(1, count - 1))
            start_x = max_left
            needed_width = piece_width + max(0, count - 1) * step
            if needed_width < usable_width:
                start_x = cx - needed_width // 2
            y = cy + int(radius * 0.23)
            warrior_drawers = {
                "marquise": make_marquise_piece,
                "eyrie": make_eyrie_piece,
                "alliance": make_alliance_piece,
                "vagabond": make_vagabond_piece,
            }
            for idx, faction in enumerate(placed_warriors):
                x = int(start_x + idx * step)
                warrior_drawers.get(faction, make_vagabond_piece)(x, y)

        def draw_supply_row(
            y_center: int,
            start_x: int,
            slots_per_row: int,
            slot_size: int,
            slot_spacing: int,
            remaining: int,
            piece_image: Image.Image,
        ) -> None:
            tile_y = y_center - slot_size // 2
            remaining = max(0, min(remaining, slots_per_row))
            first_filled_slot = slots_per_row - remaining

            for slot_idx in range(slots_per_row):
                tile_x = start_x + slot_idx * (slot_size + slot_spacing)
                draw.rectangle((tile_x, tile_y, tile_x + slot_size, tile_y + slot_size), fill=None, outline="black", width=1)
                if slot_idx >= first_filled_slot:
                    piece_x = tile_x + (slot_size - piece_image.width) // 2
                    piece_y = tile_y + (slot_size - piece_image.height) // 2
                    img.paste(piece_image, (piece_x, piece_y), piece_image)

        def draw_faction_header(board_rect: tuple[int, int, int, int], title: str, bg_color: tuple[int, int, int]) -> None:
            left, top, right, _ = board_rect
            draw.rectangle((left, top, right, top + 34), fill=bg_color, outline="black", width=2)
            draw.text((left + 8, top + 8), title, fill="white", font=font_bold)

        def draw_faction_counts(
            board_rect: tuple[int, int, int, int],
            reserve: int,
            crafted: int,
            hand_count: int,
            victory_points: int,
        ) -> int:
            left, top, _, _ = board_rect
            text_y = top + 40
            draw.text((left + 8, text_y), f"Reserve: {reserve}", fill="black", font=font)
            draw.text((left + 8, text_y + 16), f"Crafted items: {crafted}", fill="black", font=font)
            draw.text((left + 8, text_y + 32), f"Cards in hand: {hand_count}", fill="black", font=font)
            draw.text((left + 8, text_y + 48), f"Victory points: {victory_points}", fill="black", font=font)
            return text_y + 70

        def faction_data(faction_name: str) -> dict[str, Any]:
            return state_dictionary.get("factions", {}).get(faction_name, {}) or {}

        def faction_public_data(faction_name: str) -> dict[str, Any]:
            return faction_data(faction_name).get("public_data", {}) or {}

        def faction_crafted_items(faction_name: str) -> dict[str, int]:
            faction = faction_data(faction_name)
            public_data = faction.get("public_data", {}) or {}
            crafted = faction.get("crafted_items") or public_data.get("crafted_items") or {}
            return {str(item): int(count) for item, count in crafted.items() if int(count) > 0}

        def faction_crafted_cards(faction_name: str) -> list[Any]:
            faction = faction_data(faction_name)
            public_data = faction.get("public_data", {}) or {}
            return list(faction.get("crafted_cards") or public_data.get("crafted_cards") or [])

        def crafted_item_count(faction_name: str) -> int:
            return sum(faction_crafted_items(faction_name).values())

        def item_summary(items: dict[str, int]) -> str:
            if not items:
                return "-"
            return ", ".join(f"{item} x{count}" for item, count in sorted(items.items()))

        def draw_text_box(
            rect: tuple[int, int, int, int],
            title: str,
            body: str,
            fill: tuple[int, int, int],
        ) -> None:
            left, top, right, bottom = rect
            draw.rectangle(rect, fill=fill, outline="black", width=1)
            draw.text((left + 4, top + 3), title, fill="black", font=small_font)
            body_y = top + 17
            max_chars = max(8, (right - left - 8) // 6)
            lines = []
            text = body or "-"
            while text:
                lines.append(text[:max_chars])
                text = text[max_chars:]
                if len(lines) >= 2:
                    if text:
                        lines[-1] = lines[-1].rstrip() + "..."
                    break
            if not lines:
                lines = ["-"]
            for idx, line in enumerate(lines):
                if body_y + idx * 12 < bottom - 2:
                    draw.text((left + 4, body_y + idx * 12), line, fill="black", font=small_font)

        def draw_crafted_sections(
            board_rect: tuple[int, int, int, int],
            faction_name: str,
            y: int,
            fill: tuple[int, int, int],
        ) -> int:
            left, _, right, _ = board_rect
            cards = faction_crafted_cards(faction_name)
            card_text = ", ".join(card_label(card_id) for card_id in cards) if cards else "-"
            items = faction_crafted_items(faction_name)
            card_rect = (left + 8, y, right - 8, y + 38)
            item_rect = (left + 8, y + 42, right - 8, y + 80)
            draw_text_box(card_rect, "Crafted Cards", card_text, fill)
            draw_text_box(item_rect, "Crafted Items", item_summary(items), fill)
            return y + 86

        def normalize_suit_symbol(value: Any) -> str:
            v = str(value).lower()
            if v.endswith("fox") or v == "fox":
                return "fox"
            if v.endswith("rabbit") or v == "rabbit":
                return "rabbit"
            if v.endswith("mouse") or v == "mouse":
                return "mouse"
            return "bird"

        def suit_symbol_from_card_id(card_id: Any) -> str:
            if isinstance(card_id, int):
                raw_cards = state_dictionary.get("raw", {}).get("cards", {})
                card = raw_cards.get(str(card_id), {})
                if card:
                    return normalize_suit_symbol(card.get("suit", "bird"))
                observer = str(state_dictionary.get("meta", {}).get("observer") or "")
                private_data = state_dictionary.get("factions", {}).get(observer, {}).get("private_data", {}) or {}
                supporter_suits = private_data.get("supporter_suits_by_id", {}) or {}
                if str(card_id) in supporter_suits:
                    return normalize_suit_symbol(supporter_suits[str(card_id)])
                return "bird"
            return normalize_suit_symbol(card_id)

        def draw_suit_icon(symbol: str, x: int, y: int, size: int = 12) -> None:
            if symbol == "fox":
                suit_icon = Fox.resize((size, size), Image.Resampling.LANCZOS)
                img.paste(suit_icon, (x, y), suit_icon)
            elif symbol == "rabbit":
                suit_icon = Rabbit.resize((size, size), Image.Resampling.LANCZOS)
                img.paste(suit_icon, (x, y), suit_icon)
            elif symbol == "mouse":
                suit_icon = Mouse.resize((size, size), Image.Resampling.LANCZOS)
                img.paste(suit_icon, (x, y), suit_icon)
            else:
                draw.ellipse((x, y, x + size, y + size), fill=(245, 245, 100), outline="black", width=1)
                draw.text((x + size * 0.2, y + size * 0.05), "B", fill="black", font=small_font)

        def draw_marquise_board(board_rect: tuple[int, int, int, int]) -> None:
            draw_faction_header(board_rect, "Marquise de Cat", (168, 98, 24))
            marquise = state_dictionary.get("factions", {}).get("marquise", {})
            faction_data = marquise.get("public_data", {})
            draw_faction_counts(
                board_rect,
                int(faction_data.get("warriors_in_supply", 0)),
                crafted_item_count("marquise"),
                int(marquise.get("hand_count", len(marquise.get("hand") or []))),
                int(marquise.get("score", state_dictionary.get("scores", {}).get("marquise", 0))),
            )
            draw_crafted_sections(board_rect, "marquise", board_rect[1] + 112, (236, 205, 148))

            left, _, right, bottom = board_rect
            inner_rect = (left + 10, bottom - 132, right - 10, bottom - 10)
            draw.rectangle(inner_rect, fill=(223, 194, 134), outline="black", width=3)

            buildings = faction_data.get("buildings_in_supply", {})
            rows = [
                (int(buildings.get("workshop", 0)), Workshop),
                (int(buildings.get("sawmill", 0)), Sawmill),
                (int(buildings.get("recruiter", 0)), Recruiter),
            ]
            row_height = (inner_rect[3] - inner_rect[1]) // len(rows)
            slot_size, slot_spacing, slots_per_row = 18, 4, 6
            slots_width = slots_per_row * slot_size + (slots_per_row - 1) * slot_spacing
            slots_start_x = right - 18 - slots_width

            for idx, (remaining, piece_image) in enumerate(rows):
                row_center_y = inner_rect[1] + idx * row_height + row_height // 2
                draw_supply_row(row_center_y, slots_start_x, slots_per_row, slot_size, slot_spacing, remaining, piece_image)

        def draw_eyrie_board(board_rect: tuple[int, int, int, int]) -> None:
            draw_faction_header(board_rect, "Eyrie Dynasties", (40, 86, 132))
            faction = state_dictionary.get("factions", {}).get("eyrie", {})
            public_data = faction.get("public_data", {})
            cursor_y = draw_faction_counts(
                board_rect,
                int(public_data.get("warriors_in_supply", 0)),
                crafted_item_count("eyrie"),
                int(faction.get("hand_count", len(faction.get("hand") or []))),
                int(faction.get("score", state_dictionary.get("scores", {}).get("eyrie", 0))),
            )
            cursor_y = draw_crafted_sections(board_rect, "eyrie", cursor_y, (212, 227, 240))

            leader = str(public_data.get("leader", "")).capitalize()
            draw.text((board_rect[0] + 8, cursor_y), f"Leader: {leader}", fill="black", font=font)
            cursor_y += 18

            decree = public_data.get("decree", {})
            decree_rect = (board_rect[0] + 8, cursor_y, board_rect[2] - 8, cursor_y + 88)
            draw.rectangle(decree_rect, fill=(198, 218, 237), outline="black", width=2)
            categories = ["recruit", "move", "battle", "build"]
            section_w = (decree_rect[2] - decree_rect[0]) // 4
            for idx, category in enumerate(categories):
                sec_left = decree_rect[0] + idx * section_w
                sec_right = sec_left + section_w
                draw.line((sec_left, decree_rect[1], sec_left, decree_rect[3]), fill="black", width=1)
                draw.text((sec_left + 3, decree_rect[1] + 3), category.capitalize(), fill="black", font=small_font)
                decree_suits = public_data.get("decree_suits", {})
                suited_entries = decree_suits.get(category)
                if suited_entries is None:
                    suited_entries = decree.get(category, [])
                symbols = [suit_symbol_from_card_id(v) for v in suited_entries]
                for s_idx, symbol in enumerate(symbols):
                    x = sec_left + 4 + (s_idx % 3) * 10
                    y = decree_rect[1] + 16 + (s_idx // 3) * 10
                    if y + 8 < decree_rect[3] - 2:
                        draw_suit_icon(symbol, x, y)
            draw.line((decree_rect[2], decree_rect[1], decree_rect[2], decree_rect[3]), fill="black", width=1)

            inner_rect = (board_rect[0] + 10, board_rect[3] - 58, board_rect[2] - 10, board_rect[3] - 10)
            draw.rectangle(inner_rect, fill=(182, 205, 227), outline="black", width=3)
            roost_slots, slot_size, slot_spacing = 7, 18, 4
            slots_width = roost_slots * slot_size + (roost_slots - 1) * slot_spacing
            slots_start_x = board_rect[2] - 18 - slots_width
            row_center_y = (inner_rect[1] + inner_rect[3]) // 2
            roosts_remaining = int(public_data.get("roosts_in_supply", 0))
            draw_supply_row(row_center_y, slots_start_x, roost_slots, slot_size, slot_spacing, roosts_remaining, Roost)

        def draw_alliance_board(board_rect: tuple[int, int, int, int]) -> None:
            draw_faction_header(board_rect, "Woodland Alliance", (35, 80, 31))
            faction = state_dictionary.get("factions", {}).get("alliance", {})
            public_data = faction.get("public_data", {})
            cursor_y = draw_faction_counts(
                board_rect,
                int(public_data.get("warriors_in_supply", 0)),
                crafted_item_count("alliance"),
                int(faction.get("hand_count", len(faction.get("hand") or []))),
                int(faction.get("score", state_dictionary.get("scores", {}).get("alliance", 0))),
            )
            cursor_y = draw_crafted_sections(board_rect, "alliance", cursor_y, (159, 184, 136))

            officers = int(public_data.get("officers", 0))
            officer_rect = (board_rect[0] + 8, cursor_y, board_rect[2] - 42, cursor_y + 32)
            draw.rectangle(officer_rect, fill=(120, 152, 100), outline="black", width=2)
            draw.text((officer_rect[0] + 4, officer_rect[1] + 4), "Officers", fill="white", font=small_font)
            for idx in range(officers):
                ox = officer_rect[0] + 6 + (idx % 8) * 10
                oy = officer_rect[1] + 16 + (idx // 8) * 10
                draw.ellipse((ox, oy, ox + 7, oy + 7), fill=(230, 230, 230), outline="black", width=1)

            sympathy_slots = 10
            sympathy_remaining = int(public_data.get("sympathy_in_supply", 0))
            track_x = board_rect[2] - 28
            track_height = sympathy_slots * 17 - 2
            max_track_start_y = board_rect[3] - 58 - 6 - track_height
            track_start_y = min(cursor_y, max_track_start_y)
            for slot_idx in range(sympathy_slots):
                slot_top = track_start_y + slot_idx * 17
                draw.rectangle((track_x, slot_top, track_x + 18, slot_top + 15), outline="black", width=1)
                if slot_idx >= sympathy_slots - min(sympathy_remaining, sympathy_slots):
                    px = track_x + (18 - Sympathy.width) // 2
                    py = slot_top + (15 - Sympathy.height) // 2
                    img.paste(Sympathy, (px, py), Sympathy)

            inner_rect = (board_rect[0] + 10, board_rect[3] - 58, board_rect[2] - 34, board_rect[3] - 10)
            draw.rectangle(inner_rect, fill=(137, 166, 114), outline="black", width=3)
            slots_per_row, slot_size, slot_spacing = 3, 18, 8
            slots_width = slots_per_row * slot_size + (slots_per_row - 1) * slot_spacing
            slots_start_x = inner_rect[0] + ((inner_rect[2] - inner_rect[0]) - slots_width) // 2
            row_center_y = (inner_rect[1] + inner_rect[3]) // 2
            bases = public_data.get("bases_in_supply", {})
            remaining = [
                1 if bases.get("mouse", False) else 0,
                1 if bases.get("fox", False) else 0,
                1 if bases.get("rabbit", False) else 0,
            ]
            for idx, (count, piece_image) in enumerate(zip(remaining, [Mouse_base, Fox_base, Rabbit_base])):
                x = slots_start_x + idx * (slot_size + slot_spacing)
                draw.rectangle((x, row_center_y - 9, x + slot_size, row_center_y + 9), outline="black", width=1)
                if count == 1:
                    px = x + (slot_size - piece_image.width) // 2
                    py = row_center_y - 9 + (slot_size - piece_image.height) // 2
                    img.paste(piece_image, (px, py), piece_image)

        def draw_vagabond_board(board_rect: tuple[int, int, int, int]) -> None:
            draw_faction_header(board_rect, "Vagabond", (85, 85, 85))
            faction = state_dictionary.get("factions", {}).get("vagabond", {})
            public_data = faction.get("public_data", {}) or {}
            cursor_y = draw_faction_counts(
                board_rect,
                0,
                crafted_item_count("vagabond"),
                int(faction.get("hand_count", len(faction.get("hand") or []))),
                int(faction.get("score", state_dictionary.get("scores", {}).get("vagabond", 0))),
            )
            satchel = {str(item): int(count) for item, count in (public_data.get("satchel", {}) or {}).items() if int(count) > 0}
            tracks = {str(item): int(count) for item, count in (public_data.get("tracks", {}) or {}).items() if int(count) > 0}
            damaged = {str(item): int(count) for item, count in (public_data.get("damaged_items", {}) or {}).items() if int(count) > 0}
            relationships = public_data.get("relationships", {}) or {}
            combined_satchel = dict(satchel)
            for item, count in tracks.items():
                combined_satchel[item] = combined_satchel.get(item, 0) + count
            draw_text_box((board_rect[0] + 8, cursor_y, board_rect[2] - 8, cursor_y + 42), "Satchel", item_summary(combined_satchel), (200, 200, 200))
            draw_text_box((board_rect[0] + 8, cursor_y + 46, board_rect[2] - 8, cursor_y + 86), "Damaged Items", item_summary(damaged), (185, 185, 185))
            relation_text = ", ".join(f"{f}:{r}" for f, r in sorted(relationships.items())) if relationships else "-"
            draw_text_box((board_rect[0] + 8, cursor_y + 90, board_rect[2] - 8, cursor_y + 132), "Relationships", relation_text, (214, 214, 214))
            draw_crafted_sections(board_rect, "vagabond", cursor_y + 136, (196, 196, 196))

        def card_info_from_id(card_id: Any) -> tuple[str | None, str]:
            suit = suit_symbol_from_card_id(card_id)
            if not isinstance(card_id, int):
                return str(card_id), suit

            raw_cards = state_dictionary.get("raw", {}).get("cards", {}) or {}
            card = raw_cards.get(str(card_id), {}) if isinstance(raw_cards, dict) else {}
            if isinstance(card, dict) and card:
                return str(card.get("name") or card_id), normalize_suit_symbol(card.get("suit", suit))

            card = base_card_lookup.get(card_id)
            if card is not None:
                return card.name, normalize_suit_symbol(card.suit)

            return None, suit

        def card_label(card_id: Any) -> str:
            name, suit = card_info_from_id(card_id)
            if name:
                return f"{name} ({suit})"
            return str(card_id)

        def draw_observer_private_panel(panel_rect: tuple[int, int, int, int]) -> None:
            left, top, right, bottom = panel_rect
            draw.rectangle(panel_rect, fill=(248, 248, 248), outline="black", width=3)
            draw.rectangle((left, top, right, top + 30), fill=(80, 80, 80), outline="black", width=2)
            draw.text((left + 8, top + 8), "Observer Private Info", fill="white", font=font_bold)

            meta = state_dictionary.get("meta", {})
            observer = str(meta.get("observer") or "")
            if not observer:
                draw.text((left + 8, top + 42), "No observer context (full game state).", fill="black", font=font)
                return

            observer_data = state_dictionary.get("factions", {}).get(observer, {})
            private_data = observer_data.get("private_data", {}) or {}
            hand = observer_data.get("hand") or []
            hand_count = int(observer_data.get("hand_count", len(hand)))

            y = top + 40
            draw.text((left + 8, y), f"Observer: {observer.title()}", fill="black", font=font)
            y += 20
            draw.text((left + 8, y), f"Hand ({hand_count})", fill="black", font=font_bold)
            y += 16

            if hand:
                for card_id in hand:
                    if y > bottom - 18:
                        draw.text((left + 8, y), "...", fill="black", font=font)
                        return
                    draw.text((left + 16, y), f"- {card_label(card_id)}", fill="black", font=small_font)
                    y += 14
            else:
                draw.text((left + 16, y), "(hidden or empty)", fill="black", font=small_font)
                y += 16

            supporters = private_data.get("supporters") or []
            if supporters:
                y += 4
                draw.text((left + 8, y), f"Supporters ({len(supporters)})", fill="black", font=font_bold)
                y += 16
                for card_id in supporters:
                    if y > bottom - 18:
                        draw.text((left + 8, y), "...", fill="black", font=font)
                        return
                    draw.text((left + 16, y), f"- {card_label(card_id)}", fill="black", font=small_font)
                    y += 14

        def draw_discard_pile_panel(panel_rect: tuple[int, int, int, int]) -> None:
            left, top, right, bottom = panel_rect
            draw.rectangle(panel_rect, fill=(238, 238, 238), outline="black", width=2)
            draw.text((left + 8, top + 6), "Discard Pile", fill="black", font=font_bold)

            discard_pile = state_dictionary.get("cards", {}).get("discard_pile", []) or []
            draw.text((left + 8, top + 24), f"Cards: {len(discard_pile)}", fill="black", font=font)

            preview = discard_pile[-3:]
            preview_y = top + 40
            if not preview:
                draw.text((left + 8, preview_y), "(empty)", fill="black", font=small_font)
                return

            labels = [card_label(card_id) for card_id in reversed(preview)]
            preview_text = ", ".join(labels)
            draw.text((left + 8, preview_y), f"Top: {preview_text}", fill="black", font=small_font)

        state_dictionary = self.build_state_dictionary(observation)
        base_card_lookup = {card.card_id: card for card in create_base_deck()} if create_base_deck else {}

        img = Image.new("RGB", (800, 600), color="white")
        draw = ImageDraw.Draw(img)
        font = load_font(12)
        small_font = load_font(10)
        font_bold = load_font(14, bold=True)

        Workshop = Image.open("state_renderer/images/anvil_piece.png").convert("RGBA").resize((16, 16))
        Sawmill = Image.open("state_renderer/images/Sawmill.webp").convert("RGBA").resize((16, 16))
        Recruiter = Image.open("state_renderer/images/Recruiter.webp").convert("RGBA").resize((16, 16))
        Roost = Image.open("state_renderer/images/Roost.webp").convert("RGBA").resize((16, 16))
        Wood = Image.open("state_renderer/images/Wood.webp").convert("RGBA").resize((16, 16))
        Mouse_base = Image.open("state_renderer/images/Mouse_base.webp").convert("RGBA").resize((16, 16))
        Fox_base = Image.open("state_renderer/images/Fox_base.webp").convert("RGBA").resize((16, 16))
        Rabbit_base = Image.open("state_renderer/images/Rabbit_base.webp").convert("RGBA").resize((16, 16))
        Sympathy = Image.open("state_renderer/images/Sympathy.webp").convert("RGBA").resize((16, 16))

        Fox = Image.open("state_renderer/images/Fox.png").convert("RGBA").resize((8, 8))
        Rabbit = Image.open("state_renderer/images/Rabbit.png").convert("RGBA").resize((8, 8))
        Mouse = Image.open("state_renderer/images/Mouse.png").convert("RGBA").resize((8, 8))
        building_images = {
            ("marquise", "sawmill"): Sawmill,
            ("marquise", "workshop"): Workshop,
            ("marquise", "recruiter"): Recruiter,
            ("eyrie", "roost"): Roost,
            ("alliance", "mouse_base"): Mouse_base,
            ("alliance", "fox_base"): Fox_base,
            ("alliance", "rabbit_base"): Rabbit_base,
        }
        token_images = {
            ("marquise", "wood"): Wood,
            ("alliance", "sympathy"): Sympathy,
        }

        draw.rectangle((0, 0, 550, 350), fill=(85, 107, 85), outline="black", width=3)
        private_panel_rect = (550, 0, 800, 350)
        draw_observer_private_panel(private_panel_rect)
        draw_discard_pile_panel((600, 300, 800, 350))

        clearing_positions: dict[int, tuple[int, int]] = {
            1: (50, 45),
            2: (320, 45),
            3: (480, 82),
            4: (50, 140),
            5: (240, 120),
            6: (180, 195),
            7: (350, 170),
            8: (480, 195),
            9: (50, 290),
            10: (215, 300),
            11: (340, 280),
            12: (480, 300),
        }
        forest_positions: dict[int, tuple[int, int]] = {
            1: (200, 70),
            2: (285, 330),
            3: (120, 120),
            4: (410, 130),
            5: (100, 200),
            6: (380, 235),
            7: (160, 260),
            8: (455, 245),
        }
        radius = 45

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

        for forest_id, center in forest_positions.items():
            fx, fy = center
            draw.ellipse((fx - 16, fy - 11, fx + 16, fy + 11), fill=(68, 116, 68), outline=(30, 70, 30), width=1)
            draw.text((fx - 10, fy - 6), f"F{forest_id}", fill="white", font=small_font)

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
            clearing_suit = normalize_suit_symbol(clearing_data.get("suit", "bird"))
            draw_suit_icon(clearing_suit, cx + radius - 12, cy + radius - 12, size=14)

            slots = int(clearing_data.get("building_slots", 0))
            if slots > 0:
                buildings: list[tuple[str, str]] = []
                for faction in ("marquise", "eyrie", "alliance", "vagabond"):
                    for building_name in clearing_data.get("buildings", {}).get(faction, []):
                        if building_name == "base":
                            building_name = (
                                f"{clearing_suit}_base" if clearing_suit in ("mouse", "fox", "rabbit") else "base"
                            )
                        buildings.append((faction, building_name))
                add_build_spots(center, slots, buildings)

            tokens: list[tuple[str, str]] = []
            for faction in ("marquise", "eyrie", "alliance", "vagabond"):
                tokens.extend((faction, token_name) for token_name in clearing_data.get("tokens", {}).get(faction, []))
            place_tokens(center, tokens)

            warriors: list[str] = []
            for faction in ("marquise", "eyrie", "alliance", "vagabond"):
                warriors.extend([faction] * int(clearing_data.get("warriors", {}).get(faction, 0)))
            place_warriors(center, warriors)

        vagabond_public = faction_public_data("vagabond")
        raw_location = vagabond_public.get("location")
        raw_forest_location = vagabond_public.get("forest_location")
        try:
            vagabond_location = int(raw_location) if raw_location is not None else None
        except (TypeError, ValueError):
            vagabond_location = None
        try:
            forest_location = int(raw_forest_location) if raw_forest_location is not None else None
        except (TypeError, ValueError):
            forest_location = None
        if vagabond_location and vagabond_location in clearing_positions:
            cx, cy = clearing_positions[vagabond_location]
            make_vagabond_piece(cx - 11, cy + int(radius * 0.1))
        elif vagabond_location == 0 and forest_location in forest_positions:
            fx, fy = forest_positions[forest_location]
            make_vagabond_piece(fx - 11, fy + 8)

        marquise_rect = (0, 350, 200, 600)
        eyrie_rect = (200, 350, 400, 600)
        alliance_rect = (400, 350, 600, 600)
        vagabond_rect = (600, 350, 800, 600)

        draw.rectangle(marquise_rect, fill=(229, 182, 88), outline="black", width=3)
        draw.rectangle(eyrie_rect, fill=(46, 117, 179), outline="black", width=3)
        draw.rectangle(alliance_rect, fill=(53, 101, 40), outline="black", width=3)
        draw.rectangle(vagabond_rect, fill=(111, 111, 111), outline="black", width=3)

        draw_marquise_board(marquise_rect)
        draw_eyrie_board(eyrie_rect)
        draw_alliance_board(alliance_rect)
        draw_vagabond_board(vagabond_rect)

        target_size = (1600, 1200)
        if img.size != target_size:
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            img = img.resize(target_size, resample=resampling)

        img.save(output_path)

    def build_state_dictionary(self, state: Any) -> dict[str, Any]:
        """Return an easy-to-read dictionary from a state/observation object."""

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
            "forests": raw.get("forests", {}),
            "paths": raw.get("paths", []),
            "factions": raw.get("factions", {}),
            "item_supply": raw.get("item_supply", {}),
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
