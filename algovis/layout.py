"""Small, explicit layout and type conventions for hand-authored lessons.

Planning a column never adds its future rows to a scene or changes their size.
Authors reveal those rows on narration cues and animate existing rows themselves.
"""
from dataclasses import dataclass
import math

import numpy as np
from manim import MathTex, SingleStringMathTex, Text, UL

from .theme import DEFAULT_SPACING, DEFAULT_THEME


def measured_font_size(mobject):
    """Track scaling independently of a later change to the typeset glyphs."""
    if getattr(mobject,"_algovis_font_container",False):
        sizes=[measured_font_size(child) for child in mobject.submobjects
               if getattr(child,"_algovis_typography_group",None)]
        sizes=[size for size in sizes if size is not None]
        if sizes:
            return float(np.median(sizes))
    reference = getattr(mobject, "_algovis_font_reference", None)
    if reference and reference[1] > 0:
        return reference[0]*float(mobject.height)/reference[1]
    return getattr(mobject, "font_size", None)


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
            LessonStyle._watch_type(obj, peers, type_role)
        return obj

    @staticmethod
    def _watch_type(obj, peers, type_role, inherited_size=None):
        obj._algovis_type_role = type_role
        obj._algovis_typography_group = peers
        size = getattr(obj,"font_size",inherited_size)
        pieces = [child for child in obj.submobjects
                  if isinstance(getattr(child,"tex_string",None),str)]
        if pieces:
            # A multiline or partially substituted equation's total height
            # does not measure its font. Check its typeset pieces instead.
            obj._algovis_font_container = True
            for child in pieces:
                LessonStyle._watch_type(child, peers, type_role, size)
        else:
            obj._algovis_font_container = False
            if size is not None:
                obj._algovis_font_reference = (float(size),float(obj.height))

    def math(self, *tex, role="neutral", type_role="equation", peers=None, **options):
        obj = MathTex(*tex, **self._options(role, type_role, options))
        return self._mark(obj, role, type_role, peers)

    def math_like(self, reference, *tex, role="neutral", peers=None, **options):
        """Typeset a replacement at the reference's current font size.

        Unlike matching bounding-box height, this keeps a new fraction or a
        different argument at the same type size as the surrounding function.
        """
        if "font_size" in options or "color" in options:
            raise ValueError("math_like takes its size from the reference and its color from a role")
        sizes=[measured_font_size(obj) for obj in reference.get_family()]
        size=next((size for size in sizes if size is not None and size>0),None)
        if size is None:
            raise ValueError("The reference has no measurable type size")
        obj=MathTex(*tex,font_size=size,color=self.theme.role_color(role),**options)
        return self._mark(obj,role,"equation",peers)

    def text(self, text, role="neutral", type_role="body", peers=None, **options):
        if self.theme.text_font and "font" not in options:
            options["font"] = self.theme.text_font
        obj = Text(text, **self._options(role, type_role, options))
        return self._mark(obj, role, type_role, peers)

    def watch(self, peers, *mobjects, type_role="equation", kind="math"):
        """Check existing peer rows without changing their size or ownership.

        This is useful when preserving a working hand-authored layout. Mark
        outer text objects once, rather than also marking every nested glyph.
        """
        if kind not in ("math", "text"):
            raise ValueError("Peer kind must be 'math' or 'text'")
        def mark(obj):
            is_math=isinstance(obj,SingleStringMathTex) or isinstance(getattr(obj,"tex_string",None),str)
            if is_math or isinstance(obj,Text):
                if not (is_math if kind == "math" else isinstance(obj,Text)):
                    return
                self._watch_type(obj, peers, type_role)
            else:
                for child in obj.submobjects:
                    mark(child)
        for obj in mobjects:
            mark(obj)
        return mobjects[0] if len(mobjects) == 1 else mobjects

    @staticmethod
    def align_rows(group, *mobjects):
        """Declare a shared left edge, preserving each row's existing position.

        Copies do not become additional members of the alignment contract.
        They may legitimately travel to a different part of the explanation.
        """
        for obj in mobjects:
            obj._algovis_alignment_group = group
            obj._algovis_alignment_owner = id(obj)
        return mobjects[0] if len(mobjects) == 1 else mobjects


class ColumnLayout:
    """Top-to-bottom named slots inside a parent region, with one left edge.

    Reserve a row using its final content or an explicit height before animating.
    An overflow raises an error; rows are never independently shrunk to fit.
    ``place`` can prepare a replacement in the same slot without moving its peers.
    The layout deliberately has no Manim parent/child ownership side effects.
    Pass ``content_width=max(row.width for row in completed_rows)`` to center
    a left-aligned block within the region. Measure final populated rows, so
    shorter incremental reveals keep their anchor instead of drifting.
    """

    def __init__(self, region, *, padding=0, gap=DEFAULT_SPACING.relaxed, name="column",
                 content_width=None):
        if padding < 0 or gap < 0 or 2*padding >= min(region.width, region.height):
            raise ValueError("Column padding and gap must leave a positive content area")
        available_width = region.width - 2*padding
        if content_width is not None and (
                not math.isfinite(content_width) or content_width <= 0
                or content_width > available_width+1e-7):
            raise ValueError("Centered content width must fit inside the padded region")
        self.region, self.padding, self.gap, self.name = region, padding, gap, name
        self.width = available_width if content_width is None else content_width
        self.left = region.center[0] - self.width/2
        self.top = region.center[1] + region.height/2 - padding
        self.bottom = region.center[1] - region.height/2 + padding
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
