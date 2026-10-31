"""Shared, cue-neutral frames for hand-authored lessons.

These components arrange existing objects and own their mechanical transition
phases. They never choose narration triggers or mathematical content. A nested
term is revealed after its moving owner arrives, without prepainting the future
layout. Keep narration and mathematics in the scene; keep repeated geometry and
component lifecycle here.
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
                            [self.style.proof_divider_x, min(-2.93,self.rows['conclusion']-.28), 0],
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

    def label_target(self, row, first_line):
        """Plan a top-aligned row label without moving live artwork early.

        Supply the first line, rather than the full multiline body. The scene
        can adopt this target before the label's reveal or animate it on the
        same cue as a changed row. Existing content keeps its position.
        """
        key = str(row).upper().replace('_', ' ')
        return self.labels_by_name[key].copy().align_to(first_line, UP)

    def bind(self,row,content,*,first_line=None):
        """Keep a live label aligned as its retained content changes."""
        from .core.proof import bind_proof_label
        key=str(row).upper().replace('_',' ')
        return bind_proof_label(self.labels_by_name[key],content,first_line)

    def align(self,row,content,*,first_line=None):
        """Plan an animated binding; nothing visible moves before activation."""
        from .core.proof import ProofLabelAlignment
        key=str(row).upper().replace('_',' ')
        return ProofLabelAlignment(self.labels_by_name[key],content,first_line)


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
    _algovis_content_fields=('aligned_parts',)

    def __init__(self, lhs, rows, *, compact=False, show_brace=None,aligned_parts=(),theme=DEFAULT_THEME, style=None, **kwargs):
        self.theme,self.compact=theme,compact
        self.aligned_parts=tuple(aligned_parts)
        self.show_brace=show_brace
        self.style = style or DEFAULT_FRAME_STYLE
        self.lhs = lhs
        self.rows = rows if isinstance(rows, VGroup) else VGroup(*rows)
        self.rows.arrange(DOWN, aligned_edge=LEFT,
                          buff=self.style.compact_case_gap if compact else self.style.case_gap)
        self._align_parts()
        self.brace = Brace(self.rows, LEFT, color=theme.foreground)
        self.brace.set_opacity(1 if self.show_brace is True or (self.show_brace is None and len(self.rows)>1) else 0)
        lhs.next_to(self.brace, LEFT, buff=self.style.case_lhs_gap)
        super().__init__(lhs, self.brace, self.rows, **kwargs)
        self._algovis_layout_component = "CaseEquation"

    @property
    def baseline(self):
        return self.lhs.baseline

    def _align_parts(self):
        """Align named trailing annotations as actual case columns.

        A TeX quad is spacing inside one expression, not a column shared by
        alternatives of different lengths. The cases component owns this
        geometry and reapplies it whenever typography rebuilds its rows.
        """
        from .core.math_row import MathRow
        for name in self.aligned_parts:
            rows=[row for row in self.rows if isinstance(row,MathRow) and name in row.parts]
            if not rows:continue
            x=max(row.part(name).get_left()[0] for row in rows)
            for row in rows:
                keys=list(row.parts);index=keys.index(name)
                delta=x-row.part(name).get_left()[0]
                for key in keys[index:]:row.part(key).shift(RIGHT*delta)
                row._remember_layout()

    def apply_scene_typography(self,typography,*,group):
        from .layout import assign_scene_typography
        center=self.get_center()
        assign_scene_typography(self.lhs,typography,group=group)
        for row in self.rows:assign_scene_typography(row,typography,group=group)
        self.rows.arrange(DOWN,aligned_edge=LEFT,buff=self.style.compact_case_gap if self.compact else self.style.case_gap)
        self._align_parts()
        self.brace.become(Brace(self.rows,LEFT,color=self.brace.get_color()))
        self.brace.set_opacity(1 if self.show_brace is True or (self.show_brace is None and len(self.rows)>1) else 0)
        self.lhs.next_to(self.brace,LEFT,buff=self.style.case_lhs_gap)
        self.move_to(center)

    def part(self,name):
        if name=='lhs':return self.lhs
        if name=='brace':return self.brace
        if name.startswith('row:'):return self.rows[int(name.split(':')[1])]
        raise KeyError(name)

    def with_state(self,*,lhs=None,rows=None,aligned_parts=None,call=None):
        """Refine alternatives or the function call without replacing its peers.

        ``call=`` keeps the equals sign, optimizer and their term identities.
        Reconstruct ``lhs`` only when the entire left-hand side changes meaning.
        """
        if call is not None:
            if lhs is not None:
                raise ValueError("Specify call or lhs, not both")
            lhs=self.lhs.next_layout(call=call)
        return CaseEquation(lhs.copy() if lhs is not None else self.lhs.copy(),
            [row.copy() for row in (rows if rows is not None else self.rows)],
            style=self.style,theme=self.theme,compact=self.compact,show_brace=self.show_brace,
            aligned_parts=self.aligned_parts if aligned_parts is None else aligned_parts).move_to(self)

    def motions_to(self,target,*,skip=(),introductions=None,retirements=None):
        from manim import FadeIn,FadeOut,Transform,AnimationGroup,Succession
        from .core.math_row import MathRow
        from .utils.effects import DeferredAnimation
        motions=[];introduced=[];retired=[]
        for name,(old,new) in zip(['lhs',*(f'row:{index}' for index in range(len(self.rows)))],
                                [(self.lhs,target.lhs),*zip(self.rows,target.rows)]):
            ignored=tuple(path[len(name)+1:] for path in skip if path.startswith(name+'.'))
            motions.extend(old.motions_to(new,skip=ignored,introductions=introduced,retirements=retired) if isinstance(old,MathRow) and isinstance(new,MathRow)
                           else [Transform(old,new)])
        motions.append(Transform(self.brace,target.brace))
        retired.extend(FadeOut(row) for row in self.rows[len(target.rows):])
        introduced.extend(target.rows[len(self.rows):])
        if retirements is not None:
            retirements.extend(retired);retired=[]
        if introductions is not None:
            introductions.extend(introduced);introduced=[]
        # New labels belong to their moving equation, including nested rows.
        # Never leave them fading at the destination while the owner travels.
        moving=any(np.linalg.norm(a.get_center()-b.get_center())>.1
                   for old,new in [(self.lhs,target.lhs),*zip(self.rows,target.rows)]
                   for a,b in ([(old.part(key),new.part(key)) for key in old.parts.keys() & new.parts.keys()]
                               if isinstance(old,MathRow) and isinstance(new,MathRow) else [(old,new)]))
        def arrival():
            if moving and introduced:
                return Succession(AnimationGroup(*motions,run_time=.8),
                    DeferredAnimation(lambda:AnimationGroup(*(FadeIn(part) for part in introduced)),run_time=.2))
            return AnimationGroup(*motions,*(FadeIn(part) for part in introduced))
        if retired:
            return [Succession(AnimationGroup(*retired,run_time=.25),
                               DeferredAnimation(arrival,run_time=.75))]
        if moving and introduced:return [arrival()]
        motions.extend(FadeIn(part) for part in introduced)
        return motions

    def adopt_layout(self,target):
        from .composition import _adopt
        _adopt(self.lhs,target.lhs)
        self.brace.become(target.brace)
        adopted=[]
        for index,row in enumerate(target.rows):
            live=self.rows[index] if index<len(self.rows) else row.copy()
            _adopt(live,row);adopted.append(live)
        self.rows.submobjects=adopted
        self.submobjects=[self.lhs,self.brace,self.rows]
        self.aligned_parts=target.aligned_parts
        return self


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
