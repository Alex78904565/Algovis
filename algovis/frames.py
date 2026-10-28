"""Shared, cue-neutral frames for hand-authored lessons.

These components arrange existing objects. They never add future content to a
scene, schedule a reveal, shrink a formula, or replace its mathematical parts.
Keep the narration and the mathematics in the scene; keep repeated geometry here.
"""
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
from manim import Brace, DOWN, LEFT, Line, RIGHT, RoundedRectangle, Text, UL, UP, VGroup

from .theme import DEFAULT_THEME


@dataclass(frozen=True)
class LessonFrameStyle:
    """Edit these defaults once to update every use on the next render."""

    proof_label_left: float = -6.60
    proof_divider_x: float = -3.25
    proof_content_left: float = -2.95
    proof_label_size: float = 16
    equation_left: float = -5.85
    equation_right: float = 6.85
    term_gap: float = .12
    case_gap: float = .42
    compact_case_gap: float = .30
    case_lhs_gap: float = .18
    panel_radius: float = .14
    panel_stroke: float = 2.3
    panel_opacity: float = .96
    panel_title_size: float = 18
    panel_title_inset: float = .20
    marker_size: float = 14
    marker_gap: float = .10
    marker_margin: float = .28
    comparison_offset: float = 3.40


DEFAULT_FRAME_STYLE = LessonFrameStyle()


def _font(theme):
    return {"font": theme.text_font} if theme.text_font else {}


class ProofFrame:
    """One proof rail, with named slots and independently revealable labels.

    Profiles reserve different amounts of room for worked algebra or a side
    diagram. They share label typography, columns, divider and semantic colors.
    The frame has no scene ownership: moving retained work into a slot does not
    add labels, other rows, or a giant parent group to the scene.
    """

    LABELS = ("DEFINITIONS", "CLAIM", "BASE CASE", "INDUCTION HYPOTHESIS", "INDUCTIVE STEP")
    PROFILES = MappingProxyType({
        "worked": (1.82, .98, 0., -.98, -1.78),
        "detailed": (2.15, 1.12, -.40, -1.18, -2.30),
        "compact": (2.30, .72, -.78, -1.56, -2.46),
        "diagram": (2.30, 1.40, -.70, -1.55, -2.37),
    })
    EXTRA_SLOTS = MappingProxyType({
        "worked": {"meaning": 1.82, "work": -2.50, "conclusion": -3.45},
        "detailed": {"meaning": .40, "work": -2.30, "conclusion": -3.62},
        "compact": {"meaning": -.04, "work": -2.46, "conclusion": -3.45},
        "diagram": {"meaning": .80, "meaning_equals": .34, "meaning_detail": -.06,
                    "work": -2.37, "conclusion": -3.45},
    })

    def __init__(self, profile="compact", *, theme=DEFAULT_THEME, style=None):
        if profile not in self.PROFILES:
            raise ValueError(f"Unknown proof profile: {profile!r}")
        self.profile, self.theme = profile, theme
        self.style = style or DEFAULT_FRAME_STYLE
        self.rows = dict(zip(self.LABELS, self.PROFILES[profile]))
        self.rows.update(self.EXTRA_SLOTS[profile])
        self.labels = VGroup(*[
            Text(name, font_size=self.style.proof_label_size, color=theme.primary, **_font(theme))
            .move_to([self.style.proof_label_left, self.rows[name], 0], aligned_edge=LEFT)
            for name in self.LABELS
        ])
        self.labels_by_name = dict(zip(self.LABELS, self.labels))
        self.divider = Line([self.style.proof_divider_x, 2.63, 0],
                            [self.style.proof_divider_x, -2.93, 0],
                            color=theme.muted, stroke_width=1.2)
        self.chrome = VGroup(self.divider, self.labels)
        if any(label.get_right()[0] > self.style.proof_divider_x-.12 for label in self.labels):
            raise ValueError("Proof labels cross the divider; widen the shared label column")

    @property
    def left(self):
        return np.array([self.style.proof_content_left, 0., 0.])

    def anchor(self, row):
        key = row if row in self.rows else str(row).upper().replace("_", " ")
        return self.left + UP*self.rows[key]

    def place(self, row, mobject):
        mobject.move_to(self.anchor(row), aligned_edge=LEFT)
        mobject._algovis_layout_component = "ProofFrame"
        mobject._algovis_layout_row = row
        return mobject


class EquationFrame:
    """Stable, named anchors for an explanation that grows into equations.

    The three profiles describe orientation, not a particular algorithm.
    Unchanged terms remain the original objects. Use ``line`` or ``cases`` to
    prepare the complete row before revealing its individual terms on cues.
    """

    PROFILES = MappingProxyType({
        "stacked": {"meaning": .73, "recurrence": -.47, "base": -2.12},
        "split": {"meaning": 1.40, "recurrence": .50, "terms": -.48,
                  "choice": -1.58, "parameters": -3.12, "definition": 1.79},
        "inline": {"meaning": 1.65, "recurrence": -.10, "choice": -1.12,
                   "question": 2.25, "current": -1.80, "parameters": -2.48,
                   "definition": 2.08, "meaning_detail": 1.56},
    })

    def __init__(self, profile="stacked", *, theme=DEFAULT_THEME, style=None):
        if profile not in self.PROFILES:
            raise ValueError(f"Unknown equation profile: {profile!r}")
        self.profile, self.theme = profile, theme
        self.style = style or DEFAULT_FRAME_STYLE
        self.rows = dict(self.PROFILES[profile])

    @property
    def left(self):
        return np.array([self.style.equation_left, 0., 0.])

    def anchor(self, row):
        return self.left + UP*self.rows[row]

    def place(self, row, mobject):
        self.check_width(mobject)
        mobject.move_to(self.anchor(row), aligned_edge=LEFT)
        mobject._algovis_layout_component = "EquationFrame"
        mobject._algovis_layout_row = row
        return mobject

    def check_width(self, mobject):
        if mobject.width > self.style.equation_right-self.style.equation_left+1e-7:
            raise ValueError("Equation exceeds its shared content column; revise the layout, not the type size")

    def line(self, *parts, row="recurrence"):
        return self.place(row, VGroup(*parts).arrange(RIGHT, buff=self.style.term_gap))

    @staticmethod
    def align_continuation(first, continuation, first_equals, next_equals):
        """Align the equals signs, then center the completed two-row block."""
        continuation.shift(RIGHT*(first_equals.get_x()-next_equals.get_x()))
        envelope = VGroup(first, continuation)
        envelope.shift(LEFT*envelope.get_center()[0])
        return envelope


class CaseEquation(VGroup):
    """Shared lhs/brace/left-aligned alternatives, using the supplied objects."""

    def __init__(self, lhs, rows, *, compact=False, theme=DEFAULT_THEME, style=None, **kwargs):
        self.style = style or DEFAULT_FRAME_STYLE
        self.lhs = lhs
        self.rows = rows if isinstance(rows, VGroup) else VGroup(*rows)
        self.rows.arrange(DOWN, aligned_edge=LEFT,
                          buff=self.style.compact_case_gap if compact else self.style.case_gap)
        self.brace = Brace(self.rows, LEFT, color=theme.foreground)
        lhs.next_to(self.brace, LEFT, buff=self.style.case_lhs_gap)
        super().__init__(lhs, self.brace, self.rows, **kwargs)
        self._algovis_layout_component = "CaseEquation"


class PanelFrame(RoundedRectangle):
    """One repeated panel treatment; dimensions follow the content's purpose."""

    def __init__(self, width, height, *, theme=DEFAULT_THEME, style=None,
                 role="structure", variant="standard", **kwargs):
        self.theme, self.style = theme, style or DEFAULT_FRAME_STYLE
        if variant not in ("standard", "quiet", "miniature"):
            raise ValueError(f"Unknown panel variant: {variant!r}")
        opacity = {"standard": self.style.panel_opacity, "quiet": .62, "miniature": .38}[variant]
        super().__init__(width=width, height=height, corner_radius=self.style.panel_radius,
                         stroke_color=theme.role_color(role), stroke_width=self.style.panel_stroke,
                         fill_color=theme.background if variant == "miniature" else theme.surface,
                         fill_opacity=opacity, **kwargs)
        self._algovis_layout_component = "PanelFrame"

    def heading(self, text):
        return Text(text, font_size=self.style.panel_title_size,
                    color=self.theme.foreground, **_font(self.theme)).next_to(
                        self.get_top(), DOWN, buff=self.style.panel_title_inset)


class ComparisonFrame:
    """The same two-column runtime frame, including its safe divider."""

    def __init__(self, *, theme=DEFAULT_THEME, style=None):
        self.style = style or DEFAULT_FRAME_STYLE
        self.left = LEFT*self.style.comparison_offset
        self.right = RIGHT*self.style.comparison_offset
        self.divider = Line(UP*2.15, DOWN*2.55, color=theme.muted, stroke_width=1.2)

    def anchor(self, side, y):
        if side not in ("left", "right"):
            raise ValueError("A comparison side is 'left' or 'right'")
        return getattr(self, side) + UP*y


class ChapterMarker(VGroup):
    """The same small persistent section marker in every narrated clip."""

    def __init__(self, chapter, label, total=8, *, theme=DEFAULT_THEME, style=None, **kwargs):
        style = style or DEFAULT_FRAME_STYLE
        index = Text(f"{chapter}/{total}", font_size=style.marker_size, weight="BOLD",
                     color=theme.accent, **_font(theme))
        divider = Line(UP*.13, DOWN*.13, color=theme.muted, stroke_width=1.2)
        name = Text(str(label).upper(), font_size=style.marker_size,
                    color=theme.muted, **_font(theme))
        super().__init__(index, divider, name, **kwargs)
        self.arrange(RIGHT, buff=style.marker_gap).to_corner(UL, buff=style.marker_margin).set_opacity(.88)
