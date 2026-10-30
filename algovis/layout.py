"""Small, explicit layout and type conventions for hand-authored lessons.

Planning a column never adds its future rows to a scene or changes their size.
Authors reveal those rows on narration cues and animate existing rows themselves.
"""
from dataclasses import dataclass
import math

import numpy as np
from manim import MathTex, SingleStringMathTex, Text, UL

from .theme import DEFAULT_SPACING, DEFAULT_THEME
from .semantics import SemanticProperties, set_semantics


def measured_font_size(mobject):
    """Track scaling independently of a later change to the typeset glyphs."""
    if getattr(mobject,"_algovis_font_container",False):
        sizes=[measured_font_size(child) for child in mobject.submobjects
               if getattr(child,"_algovis_typography_group",None)]
        sizes=[size for size in sizes if size is not None]
        if sizes:
            return float(np.median(sizes))
    reference = getattr(mobject, "_algovis_font_reference", None)
    if reference:
        return reference[0]*float(mobject.height)/reference[1] if reference[1]>0 else reference[0]
    try:return getattr(mobject, "font_size", None)
    except ZeroDivisionError:return getattr(mobject,'_algovis_empty_font_size',None)


@dataclass(frozen=True)
class LessonTypography:
    heading: float = 38
    display: float = 54
    equation: float = 33.6
    body: float = 26
    label: float = 20
    note: float = 18
    proof_label: float = 16

    def size(self, role):
        if role not in self.__dataclass_fields__:
            raise ValueError(f"Unknown typography role: {role!r}")
        return getattr(self, role)


def assign_scene_typography(mobject, typography, *, group, role=None):
    """Assign a detached object's natural size before its scene lays it out.

    A component can own internal geometry and expose its own typography hook.
    Plain equation/text objects always receive a scene role, including operators.
    No visible source object is mutated while a future scene is prepared.
    """
    hook = getattr(type(mobject), 'apply_scene_typography', None)
    if hook is not None:
        hook(mobject, typography, group=group)
        return mobject
    if isinstance(mobject, (Text, SingleStringMathTex)):
        chosen = role or getattr(mobject, '_algovis_type_role', None)
        chosen = chosen or ('body' if isinstance(mobject, Text) else 'equation')
        factor = float(getattr(mobject, '_algovis_relative_font_scale', 1.))
        size = measured_font_size(mobject)
        if size and size > 0 and mobject.height>0:
            mobject.scale(typography.size(chosen)*factor/size)
        mobject._algovis_scene_typography = True
        mobject._algovis_type_role = chosen
        LessonStyle._watch_type(mobject, group, chosen,
                                typography.size(chosen)*factor)
    elif not mobject.has_points() and mobject.submobjects:
        # Layout containers are not a typography escape hatch. Semantic
        # components with painted frames retain their internal label policy.
        for child in mobject.submobjects:
            assign_scene_typography(child, typography, group=group, role=role)
    return mobject


@dataclass(frozen=True)
class LessonStyle:
    """One palette and type scale; peer groups opt into render-time size checks."""

    theme: object = DEFAULT_THEME
    typography: LessonTypography = LessonTypography()

    def _options(self, role, type_role, options, semantics=None):
        if "font_size" in options or "color" in options:
            raise ValueError("Use typography and semantic roles instead of a local size/color override")
        return dict(font_size=self.typography.size(type_role),
                    color=(semantics or SemanticProperties(role=role)).color(self.theme), **options)

    @staticmethod
    def _mark(obj, role, type_role, peers):
        obj._algovis_semantic_role = role
        obj._algovis_type_role = type_role
        LessonStyle._watch_type(obj, peers or f'component/{role}/{type_role}', type_role)
        return obj

    @staticmethod
    def _watch_type(obj, peers, type_role, inherited_size=None):
        obj._algovis_type_role = type_role
        obj._algovis_typography_group = peers
        try:size=getattr(obj,'font_size',inherited_size)
        except ZeroDivisionError:size=getattr(obj,'_algovis_empty_font_size',inherited_size)
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

    def math(self, *tex, role="neutral", type_role="equation", peers=None,
             status=None, evaluation=None, semantics=None, **options):
        properties = semantics or SemanticProperties(role, status, evaluation)
        obj = MathTex(*tex, **self._options(role, type_role, options, properties))
        set_semantics(obj, properties, theme=self.theme)
        return self._mark(obj, properties.role, type_role, peers)

    def math_like(self, reference, *tex, role="neutral", peers=None,
                  status=None, evaluation=None, semantics=None, **options):
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
        properties = semantics or SemanticProperties(role,status,evaluation)
        obj=MathTex(*tex,font_size=size,color=properties.color(self.theme),**options)
        set_semantics(obj,properties,theme=self.theme)
        return self._mark(obj,properties.role,"equation",peers)

    def text(self, text, role="neutral", type_role="body", peers=None,
             status=None, evaluation=None, semantics=None, **options):
        if self.theme.text_font and "font" not in options:
            options["font"] = self.theme.text_font
        properties = semantics or SemanticProperties(role,status,evaluation)
        obj = Text(text, **self._options(role, type_role, options, properties))
        set_semantics(obj,properties,theme=self.theme)
        return self._mark(obj, properties.role, type_role, peers)

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
                 content_width=None, content_height=None):
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
        if content_height is not None:
            if not math.isfinite(content_height) or not 0 < content_height <= region.height-2*padding+1e-7:
                raise ValueError('Centered content height must fit inside the padded region')
            self.top = region.center[1] + content_height/2
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
