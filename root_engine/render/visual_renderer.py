"""SVG-based visual renderer kept fully separate from core engine logic."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from root_engine.enums import Faction
from root_engine.models import GameState
from root_engine.observation import Observation
from root_engine.render.visual_config import (
    BOARD_ORIGIN_X,
    BOARD_ORIGIN_Y,
    BOARD_PANEL_WIDTH,
    BOARD_SIZE,
    BUILDING_ABBREVIATIONS,
    CLEARING_COORDS,
    FACTION_COLORS,
    SUIT_COLORS,
    TOKEN_ABBREVIATIONS,
)


@dataclass
class VisualRenderer:
    """Render a GameState or Observation into an SVG frame."""

    width: int = BOARD_SIZE[0]
    height: int = BOARD_SIZE[1]

    def render(self, view: GameState | Observation) -> str:
        return self.render_frame(view)

    def render_frame(self, view: GameState | Observation) -> str:
        if isinstance(view, GameState):
            payload = _StatePayload.from_state(view)
        else:
            payload = _StatePayload.from_observation(view)

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">',
            '<rect width="100%" height="100%" fill="#f8f9f9"/>',
            self._render_header(payload),
            self._render_paths(payload),
            self._render_clearings(payload),
            self._render_side_panel(payload),
            "</svg>",
        ]
        return "\n".join(parts)

    def render_to_file(self, view: GameState | Observation, path: str) -> None:
        with open(path, "w", encoding="utf-8") as svg_file:
            svg_file.write(self.render_frame(view))

    def _render_header(self, payload: "_StatePayload") -> str:
        observer = f" | Observer: {payload.observer.value}" if payload.observer else ""
        decision_bits = [payload.decision.get("decision_type", "main_action")]
        for key in ["selected_source", "selected_destination", "selected_battle_clearing"]:
            if payload.decision.get(key) is not None:
                decision_bits.append(f"{key}={payload.decision[key]}")
        decision_text = ", ".join(decision_bits)
        score_text = "  ".join(f"{f.value}: {payload.scores[f]}" for f in Faction)
        return "\n".join(
            [
                f'<text x="{BOARD_ORIGIN_X}" y="20" font-size="14" fill="#1f2d3d">Round {payload.round_number} | {payload.current_faction.value} | {payload.current_phase}{observer}</text>',
                f'<text x="{BOARD_ORIGIN_X}" y="40" font-size="12" fill="#1f2d3d">Decision: {escape(decision_text)}</text>',
                f'<text x="{BOARD_ORIGIN_X}" y="58" font-size="12" fill="#1f2d3d">Scores: {escape(score_text)}</text>',
            ]
        )

    def _render_paths(self, payload: "_StatePayload") -> str:
        lines: list[str] = []
        seen: set[tuple[int, int]] = set()
        for cid, clearing in payload.clearings.items():
            x1, y1 = CLEARING_COORDS.get(cid, (0, 0))
            for adjacent in clearing.adjacent_clearings:
                edge = tuple(sorted((cid, adjacent)))
                if edge in seen or adjacent not in CLEARING_COORDS:
                    continue
                seen.add(edge)
                x2, y2 = CLEARING_COORDS[adjacent]
                lines.append(
                    f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#95a5a6" stroke-width="3" />'
                )
        return "\n".join(lines)

    def _render_clearings(self, payload: "_StatePayload") -> str:
        blocks: list[str] = []
        for cid in sorted(payload.clearings):
            clearing = payload.clearings[cid]
            x, y = CLEARING_COORDS.get(cid, (0, 0))
            suit_fill = SUIT_COLORS.get(clearing.suit, "#ecf0f1")
            ruler_color = FACTION_COLORS.get(clearing.ruler, "#34495e") if clearing.ruler else "#34495e"
            blocks.append(
                f'<circle cx="{x}" cy="{y}" r="56" fill="{suit_fill}" stroke="{ruler_color}" stroke-width="4" />'
            )
            blocks.append(
                f'<text x="{x - 45}" y="{y - 28}" font-size="12" fill="#2c3e50">C{cid} • {clearing.suit.value}</text>'
            )
            ruler_label = clearing.ruler.value if clearing.ruler else "none"
            blocks.append(
                f'<text x="{x - 45}" y="{y - 12}" font-size="11" fill="#2c3e50">ruler: {ruler_label}</text>'
            )

            row_y = y + 6
            blocks.extend(self._render_warriors(clearing.warriors, x - 46, row_y))
            blocks.extend(self._render_labeled_row(clearing.buildings, x - 46, row_y + 16, "B"))
            blocks.extend(self._render_labeled_row(clearing.tokens, x - 46, row_y + 32, "T"))
        return "\n".join(blocks)

    def _render_warriors(self, warriors: dict[Faction, int], x: int, y: int) -> list[str]:
        bits: list[str] = []
        offset = 0
        for faction in Faction:
            count = warriors.get(faction, 0)
            if count <= 0:
                continue
            color = FACTION_COLORS[faction]
            bits.append(
                f'<rect x="{x + offset}" y="{y - 9}" width="12" height="12" rx="2" fill="{color}" />'
            )
            bits.append(
                f'<text x="{x + offset + 15}" y="{y + 1}" font-size="10" fill="#1f2d3d">{faction.value[:3]}:{count}</text>'
            )
            offset += 58
        if not bits:
            bits.append(f'<text x="{x}" y="{y + 1}" font-size="10" fill="#7f8c8d">warriors: -</text>')
        return bits

    def _render_labeled_row(
        self,
        by_faction: dict[Faction, list[str]],
        x: int,
        y: int,
        prefix: str,
    ) -> list[str]:
        bits: list[str] = []
        offset = 0
        for faction in Faction:
            values = by_faction.get(faction, [])
            if not values:
                continue
            color = FACTION_COLORS[faction]
            labels = [
                BUILDING_ABBREVIATIONS.get(value, TOKEN_ABBREVIATIONS.get(value, value)) for value in values
            ]
            merged = "/".join(labels)
            bits.append(
                f'<circle cx="{x + offset + 5}" cy="{y - 4}" r="4" fill="{color}" />'
            )
            bits.append(
                f'<text x="{x + offset + 12}" y="{y}" font-size="10" fill="#1f2d3d">{prefix}-{faction.value[:3]}:{escape(merged)}</text>'
            )
            offset += 120
        if not bits:
            bits.append(f'<text x="{x}" y="{y}" font-size="10" fill="#7f8c8d">{prefix}: -</text>')
        return bits

    def _render_side_panel(self, payload: "_StatePayload") -> str:
        panel_x = BOARD_ORIGIN_X + BOARD_PANEL_WIDTH
        lines = [
            f'<rect x="{panel_x}" y="20" width="{self.width - panel_x - 20}" height="{self.height - 40}" fill="#ffffff" stroke="#d5d8dc"/>',
            f'<text x="{panel_x + 12}" y="42" font-size="14" fill="#17202a">Faction Status</text>',
        ]
        y = 66
        for faction in Faction:
            board = payload.factions[faction]
            lines.append(
                f'<text x="{panel_x + 12}" y="{y}" font-size="12" fill="{FACTION_COLORS[faction]}">{faction.value.title()}</text>'
            )
            y += 16
            hand_text = board.hand if board.hand is not None else f"hidden({board.hand_count})"
            lines.append(
                f'<text x="{panel_x + 20}" y="{y}" font-size="10" fill="#1f2d3d">VP {board.score} | hand {escape(str(hand_text))}</text>'
            )
            y += 14
            lines.append(
                f'<text x="{panel_x + 20}" y="{y}" font-size="10" fill="#1f2d3d">crafted: {escape(str(board.crafted_effects))}</text>'
            )
            y += 14
            if board.public_data:
                lines.append(
                    f'<text x="{panel_x + 20}" y="{y}" font-size="10" fill="#34495e">public: {escape(str(board.public_data))}</text>'
                )
                y += 14
            if board.private_data:
                lines.append(
                    f'<text x="{panel_x + 20}" y="{y}" font-size="10" fill="#34495e">private: {escape(str(board.private_data))}</text>'
                )
                y += 14
            y += 8

        lines.append(
            f'<text x="{panel_x + 12}" y="{self.height - 22}" font-size="10" fill="#566573">Discard: {escape(str(payload.discard_pile))}</text>'
        )
        return "\n".join(lines)


@dataclass
class _ClearingPayload:
    suit: object
    adjacent_clearings: list[int]
    warriors: dict[Faction, int]
    buildings: dict[Faction, list[str]]
    tokens: dict[Faction, list[str]]
    ruler: Faction | None


@dataclass
class _FactionPayload:
    score: int
    hand_count: int
    hand: list[int] | None
    crafted_effects: list[str]
    public_data: dict[str, object]
    private_data: dict[str, object]


@dataclass
class _StatePayload:
    clearings: dict[int, _ClearingPayload]
    scores: dict[Faction, int]
    discard_pile: list[int]
    current_faction: Faction
    current_phase: str
    round_number: int
    decision: dict[str, object]
    factions: dict[Faction, _FactionPayload]
    observer: Faction | None

    @classmethod
    def from_state(cls, state: GameState) -> "_StatePayload":
        clearings = {
            cid: _ClearingPayload(
                suit=clearing.suit,
                adjacent_clearings=list(clearing.adjacent_clearings),
                warriors=dict(state.board.warriors[cid]),
                buildings={f: [b.value for b in state.board.buildings[cid][f]] for f in Faction},
                tokens={f: [t.value for t in state.board.tokens[cid][f]] for f in Faction},
                ruler=_compute_ruler(
                    state.board.warriors[cid],
                    {f: [b.value for b in state.board.buildings[cid][f]] for f in Faction},
                ),
            )
            for cid, clearing in state.board.clearings.items()
        }
        factions = {
            faction: _FactionPayload(
                score=state.scores[faction],
                hand_count=len(state.faction_state(faction).hand),
                hand=list(state.faction_state(faction).hand),
                crafted_effects=list(state.faction_state(faction).crafted_effects),
                public_data={},
                private_data={},
            )
            for faction in Faction
        }
        return cls(
            clearings=clearings,
            scores=dict(state.scores),
            discard_pile=list(state.discard_pile),
            current_faction=state.turn.current_faction,
            current_phase=state.turn.phase.value,
            round_number=state.turn.round_number,
            decision={
                "decision_type": state.decision_context.decision_type.value,
                "selected_source": state.decision_context.selected_source,
                "selected_destination": state.decision_context.selected_destination,
                "selected_battle_clearing": state.decision_context.selected_battle_clearing,
            },
            factions=factions,
            observer=None,
        )

    @classmethod
    def from_observation(cls, obs: Observation) -> "_StatePayload":
        clearings = {
            cid: _ClearingPayload(
                suit=clearing.suit,
                adjacent_clearings=list(clearing.adjacent_clearings),
                warriors=dict(clearing.warriors),
                buildings={f: list(clearing.buildings[f]) for f in Faction},
                tokens={f: list(clearing.tokens[f]) for f in Faction},
                ruler=clearing.ruler,
            )
            for cid, clearing in obs.clearings.items()
        }
        factions = {
            faction: _FactionPayload(
                score=obs.factions[faction].score,
                hand_count=obs.factions[faction].hand_count,
                hand=obs.factions[faction].hand,
                crafted_effects=list(obs.factions[faction].crafted_effects),
                public_data=dict(obs.factions[faction].public_data),
                private_data=dict(obs.factions[faction].private_data),
            )
            for faction in Faction
        }
        return cls(
            clearings=clearings,
            scores=dict(obs.scores),
            discard_pile=list(obs.discard_pile),
            current_faction=obs.current_faction,
            current_phase=obs.current_phase,
            round_number=obs.round_number,
            decision=dict(obs.decision),
            factions=factions,
            observer=obs.observer,
        )


def _compute_ruler(warriors: dict[Faction, int], buildings: dict[Faction, list[str]]) -> Faction | None:
    rule_counts = {
        faction: warriors.get(faction, 0) + len(buildings.get(faction, []))
        for faction in [Faction.MARQUISE, Faction.EYRIE, Faction.ALLIANCE]
    }
    top = max(rule_counts.values())
    if top == 0:
        return None
    leaders = [f for f, count in rule_counts.items() if count == top]
    return leaders[0] if len(leaders) == 1 else None
