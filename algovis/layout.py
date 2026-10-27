"""Small, explicit layout and type conventions for hand-authored lessons.

Planning a column never adds its future rows to a scene or changes their size.
Authors reveal those rows on narration cues and animate existing rows themselves.
"""
from dataclasses import dataclass
import math

import numpy as np
from manim import MathTex, Text, UL

from .theme import DEFAULT_SPACING, DEFAULT_THEME


@dataclass(frozen=True)
class LessonTypography:
    equation: float = 33.6
    body: float = 26
    label: float = 20
    note: float = 18

    def size(self, role):
        if role not in ("equation", "body", "label", "note"):
            raise ValueError(f"Unknown typography role: {role!r}")
        return getattr(self, role)


@dataclass(frozen=True)
class LessonStyle:
    """One palette and type scale; peer groups opt into render-time size checks."""

    theme: object = DEFAULT_THEME
    typography: LessonTypography = LessonTypography()

    def _options(self, role, type_role, options):
        if "font_size" in options or "color" in options:
            raise ValueError("Use typography and semantic roles instead of a local size/color override")
        return dict(font_size=self.typography.size(type_role),
                    color=self.theme.role_color(role), **options)

    @staticmethod
    def _mark(obj, role, type_role, peers):
        obj._algovis_semantic_role = role
        obj._algovis_type_role = type_role
        if peers:
            obj._algovis_typography_group = peers
        return obj

    def math(self, *tex, role="neutral", type_role="equation", peers=None, **options):
        obj = MathTex(*tex, **self._options(role, type_role, options))
        return self._mark(obj, role, type_role, peers)

    def text(self, text, role="neutral", type_role="body", peers=None, **options):
        if self.theme.text_font and "font" not in options:
            options["font"] = self.theme.text_font
        obj = Text(text, **self._options(role, type_role, options))
        return self._mark(obj, role, type_role, peers)


class ColumnLayout:
    """Top-to-bottom named slots inside a parent region, with one left edge.

    Reserve a row using its final content or an explicit height before animating.
    An overflow raises an error; rows are never independently shrunk to fit.
    ``place`` can prepare a replacement in the same slot without moving its peers.
    The layout deliberately has no Manim parent/child ownership side effects.
    """

    def __init__(self, region, *, padding=0, gap=DEFAULT_SPACING.relaxed, name="column"):
        if padding < 0 or gap < 0 or 2*padding >= min(region.width, region.height):
            raise ValueError("Column padding and gap must leave a positive content area")
        self.region, self.padding, self.gap, self.name = region, padding, gap, name
        self.left = region.center[0] - region.width/2 + padding
        self.top = region.center[1] + region.height/2 - padding
        self.bottom = region.center[1] - region.height/2 + padding
        self.width = region.width - 2*padding
        self._cursor = self.top
        self._slots = {}

    def reserve(self, key, height, *, gap=None):
        gap = self.gap if gap is None else gap
        if key in self._slots:
            raise ValueError(f"Duplicate layout row: {key!r}")
        if not math.isfinite(height) or height <= 0 or not math.isfinite(gap) or gap < 0:
            raise ValueError("Row height must be positive and gap must be nonnegative")
        if self._cursor-height < self.bottom-1e-7:
            raise ValueError(f"{self.name}/{key} exceeds its column height; revise the layout")
        self._slots[key] = (self._cursor, height)
        self._cursor -= height+gap
        return self

    def place(self, key, mobject):
        top, height = self._slots[key]
        if mobject.width > self.width+1e-7 or mobject.height > height+1e-7:
            raise ValueError(f"{self.name}/{key} does not fit at its current type size; revise the layout")
        mobject.move_to(np.array([self.left, top, self.region.center[2]]), aligned_edge=UL)
        mobject._algovis_layout = self.name
        mobject._algovis_layout_row = key
        return mobject

    def add(self, key, mobject, *, height=None, gap=None):
        if mobject.width > self.width+1e-7:
            raise ValueError(f"{self.name}/{key} exceeds its column width; revise the layout")
        height = mobject.height if height is None else height
        if mobject.height > height+1e-7:
            raise ValueError(f"{self.name}/{key} exceeds its reserved row height")
        self.reserve(key, height, gap=gap)
        return self.place(key, mobject)
