"""Concrete story visuals that introduce an algorithmic problem before notation.

The objects in this module deliberately separate a story's cast and props from
its mathematical conclusion.  Authors can begin with recognizable objects,
animate choices in that world, and reveal weights, values, and constraints only
when the narration is ready to formalize the problem.
"""

from dataclasses import dataclass
import math

from manim import (
    AnimationGroup, Arc, Circle, Create, Cross, DashedLine, Dot, DOWN, Ellipse,
    FadeIn, FadeOut, GREEN_B, Indicate, LaggedStart, LEFT, Line, MathTex,
    MoveAlongPath, ORIGIN, PI, Polygon, RED_B, RIGHT, RoundedRectangle,
    Succession, Text, Transform, TransformFromCopy, UP, VGroup, WHITE,
)

from ..theme import DEFAULT_THEME


@dataclass(frozen=True)
class StoryItemSpec:
    """A concrete object that can later become an optimization item."""

    key: str
    label: str
    weight: float
    value: float
    icon: str = "box"
    color: object | None = None


@dataclass(frozen=True)
class StoryDecision:
    """One demonstrated accept/reject decision in a capacity story."""

    item_key: str
    accepted: bool
    message: str


@dataclass(frozen=True)
class StoryBeat:
    """One animation beat with timing metadata for a lesson workflow."""

    animation: object
    run_time: float = 0.8
    pause_after: float = 0.12


def _number(value):
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


class StoryItem(VGroup):
    """An illustrated object with optional weight and value badges."""

    def __init__(self, spec, *, theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.spec = spec
        self.theme = theme
        color = spec.color or theme.accent

        self.frame = RoundedRectangle(
            width=2.12, height=1.52, corner_radius=0.12,
            color=theme.node, fill_color=theme.surface, fill_opacity=0.96,
            stroke_width=1.8,
        )
        self.icon = self.make_icon(spec.icon, color, theme)
        self.icon.scale_to_fit_height(0.62).move_to(UP * 0.30)
        self.name = Text(spec.label, font_size=17, color=theme.foreground)
        self.name.move_to(DOWN * 0.20)
        self.metrics = VGroup(
            MathTex(rf"w={_number(spec.weight)}", color=theme.muted).scale(0.39),
            MathTex(rf"v={_number(spec.value)}", color=theme.accent).scale(0.39),
        ).arrange(RIGHT, buff=0.22).move_to(DOWN * 0.53)
        self.core = VGroup(self.frame, self.icon, self.name)
        self.add(self.frame, self.icon, self.name, self.metrics)

    @staticmethod
    def make_icon(kind, color, theme):
        """Return a compact vector icon; callers may also use the generic box."""
        if kind == "jewelry":
            gem = Polygon(
                LEFT * 0.38 + UP * 0.10,
                LEFT * 0.20 + UP * 0.36,
                RIGHT * 0.20 + UP * 0.36,
                RIGHT * 0.38 + UP * 0.10,
                DOWN * 0.40,
                color=color,
            ).set_fill(color, opacity=0.28)
            facets = VGroup(
                Line(gem.get_vertices()[0], gem.get_vertices()[2], color=color),
                Line(gem.get_vertices()[3], gem.get_vertices()[1], color=color),
                Line(gem.get_vertices()[1], gem.get_vertices()[4], color=color),
                Line(gem.get_vertices()[2], gem.get_vertices()[4], color=color),
            ).set_stroke(width=1.2)
            return VGroup(gem, facets)

        if kind == "laptop":
            screen = RoundedRectangle(
                width=1.02, height=0.62, corner_radius=0.06,
                color=color, fill_color=theme.background, fill_opacity=1,
                stroke_width=2,
            )
            glow = RoundedRectangle(
                width=0.82, height=0.42, corner_radius=0.03,
                color=theme.primary, fill_color=theme.primary, fill_opacity=0.18,
                stroke_width=1,
            ).move_to(screen)
            base = Polygon(
                LEFT * 0.60 + DOWN * 0.36, RIGHT * 0.60 + DOWN * 0.36,
                RIGHT * 0.48 + DOWN * 0.24, LEFT * 0.48 + DOWN * 0.24,
                color=color,
            ).set_fill(color, opacity=0.22)
            return VGroup(screen, glow, base)

        if kind == "cash":
            back = RoundedRectangle(
                width=1.02, height=0.55, corner_radius=0.06,
                color=theme.success, fill_color=theme.success, fill_opacity=0.12,
            ).shift(UP * 0.10 + RIGHT * 0.10)
            front = back.copy().shift(DOWN * 0.16 + LEFT * 0.16)
            dollar = Text("$", font_size=27, color=theme.success).move_to(front)
            return VGroup(back, front, dollar)

        if kind == "toilet_paper":
            roll = Circle(
                radius=0.38, color=color, fill_color=WHITE, fill_opacity=0.86,
                stroke_width=2,
            )
            hole = Circle(
                radius=0.12, color=theme.muted,
                fill_color=theme.background, fill_opacity=1, stroke_width=1.5,
            ).move_to(roll)
            sheet = RoundedRectangle(
                width=0.48, height=0.52, corner_radius=0.05,
                color=color, fill_color=WHITE, fill_opacity=0.72,
                stroke_width=1.5,
            ).next_to(roll, RIGHT, buff=-0.08).shift(DOWN * 0.13)
            perforation = DashedLine(
                sheet.get_top(), sheet.get_bottom(), color=theme.muted,
                dash_length=0.05, stroke_width=1,
            ).shift(RIGHT * 0.06)
            return VGroup(sheet, perforation, roll, hole)

        box = RoundedRectangle(
            width=0.80, height=0.66, corner_radius=0.06,
            color=color, fill_color=color, fill_opacity=0.18,
        )
        ribbon = VGroup(
            Line(box.get_top(), box.get_bottom(), color=color),
            Line(box.get_left(), box.get_right(), color=color),
        ).set_stroke(width=2)
        return VGroup(box, ribbon)

    def reveal(self):
        return FadeIn(self.core, shift=UP * 0.06)

    def reveal_metrics(self):
        return FadeIn(self.metrics, shift=UP * 0.04)


class ThiefCharacter(VGroup):
    """A friendly illustrated burglar, kept vector-native for clean scaling."""

    def __init__(self, *, theme=DEFAULT_THEME, label="THIEF", **kwargs):
        super().__init__(**kwargs)
        skin = "#F2C7A5"
        face = Circle(
            radius=0.47, color=skin,
            fill_color=skin, fill_opacity=1.0, stroke_width=1.6,
        ).shift(UP * 0.76)
        beanie = Arc(
            radius=0.49, start_angle=0, angle=PI,
            color=theme.primary, stroke_width=12,
        ).move_to(face).shift(UP * 0.09)
        beanie_band = RoundedRectangle(
            width=0.96, height=0.16, corner_radius=0.05,
            color=theme.primary, fill_color=theme.primary,
            fill_opacity=0.95, stroke_width=0,
        ).move_to(face.get_top() + DOWN * 0.13)
        mask = RoundedRectangle(
            width=0.78, height=0.25, corner_radius=0.10,
            color=theme.background, fill_color=theme.background,
            fill_opacity=0.96, stroke_width=0,
        ).move_to(face).shift(UP * 0.04)
        eye_whites = VGroup(
            Ellipse(width=0.19, height=0.10, color=WHITE,
                    fill_color=WHITE, fill_opacity=1, stroke_width=0),
            Ellipse(width=0.19, height=0.10, color=WHITE,
                    fill_color=WHITE, fill_opacity=1, stroke_width=0),
        ).arrange(RIGHT, buff=0.16).move_to(mask)
        pupils = VGroup(
            Dot(eye_whites[0].get_center(), radius=0.026,
                color=theme.background),
            Dot(eye_whites[1].get_center(), radius=0.026,
                color=theme.background),
        )
        body = RoundedRectangle(
            width=1.38, height=1.42, corner_radius=0.24,
            color=theme.primary, fill_color=theme.surface,
            fill_opacity=1.0, stroke_width=2.2,
        ).shift(DOWN * 0.43)
        stripes = VGroup(*[
            Line(LEFT * 0.62, RIGHT * 0.62, color=theme.foreground,
                 stroke_width=4).shift(DOWN * y)
            for y in (0.02, 0.38, 0.74)
        ])
        arms = VGroup(
            Line(LEFT * 0.58 + DOWN * 0.05,
                 LEFT * 1.00 + DOWN * 0.64,
                 color=theme.primary, stroke_width=10),
            Line(RIGHT * 0.58 + DOWN * 0.05,
                 RIGHT * 1.00 + DOWN * 0.48,
                 color=theme.primary, stroke_width=10),
        )
        legs = VGroup(
            Line(LEFT * 0.28 + DOWN * 1.10,
                 LEFT * 0.40 + DOWN * 1.62,
                 color=theme.primary, stroke_width=10),
            Line(RIGHT * 0.28 + DOWN * 1.10,
                 RIGHT * 0.40 + DOWN * 1.62,
                 color=theme.primary, stroke_width=10),
        )
        tag = Text(label, font_size=16, color=theme.muted)
        tag.next_to(legs, DOWN, buff=0.12)
        self.add(arms, legs, body, stripes, face, beanie, beanie_band,
                 mask, eye_whites, pupils, tag)


class CapacityBag(VGroup):
    """A container with a live capacity meter and animated stored contents."""

    def __init__(self, capacity, *, theme=DEFAULT_THEME, label="BAG", **kwargs):
        super().__init__(**kwargs)
        self.capacity = float(capacity)
        self.used = 0.0
        self.theme = theme

        self.body = Ellipse(
            width=2.12, height=1.78,
            color=theme.primary, fill_color=theme.surface, fill_opacity=0.98,
            stroke_width=2.4,
        ).shift(DOWN * 0.24)
        neck = Polygon(
            LEFT * 0.40 + UP * 1.02, RIGHT * 0.40 + UP * 1.02,
            RIGHT * 0.63 + UP * 0.58, LEFT * 0.63 + UP * 0.58,
            color=theme.primary,
        ).set_fill(theme.node, opacity=0.50)
        tie = Arc(radius=0.48, start_angle=PI, angle=PI, color=theme.accent)
        tie.stretch(0.35, dim=1).move_to(UP * 0.77)
        patch = Circle(
            radius=0.34, color=theme.accent,
            fill_color=theme.accent, fill_opacity=0.10, stroke_width=1.8,
        ).move_to(DOWN * 0.28)
        mark = Text("$", font_size=27, color=theme.accent).move_to(patch)
        bag_label = Text(label, font_size=16, color=theme.muted)
        bag_label.next_to(self.body, DOWN, buff=0.12)
        self.shell = VGroup(self.body, neck, tie, patch, mark, bag_label)

        self.gauge_outline = RoundedRectangle(
            width=0.34, height=1.62, corner_radius=0.07,
            color=theme.muted, fill_opacity=0, stroke_width=1.6,
        ).next_to(self.body, RIGHT, buff=0.30).shift(UP * 0.02)
        self.fill = self._make_fill(0)
        self.capacity_label = MathTex(
            rf"C={_number(self.capacity)}", color=theme.accent,
        ).scale(0.43).next_to(self.gauge_outline, UP, buff=0.12)
        self.readout = self._make_readout(0)
        self.capacity_parts = VGroup(
            self.gauge_outline, self.fill, self.capacity_label, self.readout,
        )
        self.contents = VGroup()
        self.add(self.shell, self.capacity_parts, self.contents)

    def _make_fill(self, used):
        inner_height = 1.44
        ratio = min(1.0, max(0.0, used / self.capacity))
        height = max(0.018, inner_height * ratio)
        fill = RoundedRectangle(
            width=0.20, height=height, corner_radius=0.03,
            stroke_width=0, fill_color=self.theme.success,
            fill_opacity=0.88 if used > 0 else 0,
        )
        bottom = self.gauge_outline.get_bottom() + UP * 0.09
        fill.move_to(bottom + UP * height / 2)
        return fill

    def _make_readout(self, used):
        return MathTex(
            rf"{_number(used)}/{_number(self.capacity)}",
            color=self.theme.foreground,
        ).scale(0.38).next_to(self.gauge_outline, DOWN, buff=0.12)

    def reveal_shell(self):
        return FadeIn(self.shell, shift=UP * 0.06)

    def reveal_capacity(self):
        return FadeIn(self.capacity_parts, shift=LEFT * 0.05)

    def add_item(self, item):
        """Animate a copy of ``item`` into the next bag slot and update usage."""
        new_used = self.used + float(item.spec.weight)
        if new_used > self.capacity:
            raise ValueError("Accepted story item would exceed container capacity")
        slot_index = len(self.contents)
        slot_offsets = (
            LEFT * 0.50 + DOWN * 0.48,
            DOWN * 0.48,
            RIGHT * 0.50 + DOWN * 0.48,
            LEFT * 0.25 + UP * 0.06,
            RIGHT * 0.25 + UP * 0.06,
        )
        destination = item.icon.copy()
        destination.scale_to_fit_height(0.38)
        destination.move_to(self.body.get_center() + slot_offsets[slot_index % len(slot_offsets)])
        self.contents.add(destination)

        next_fill = self._make_fill(new_used)
        next_readout = self._make_readout(new_used)
        self.used = new_used
        return AnimationGroup(
            # Animate a detached snapshot.  Using the nested source object
            # directly lets Manim detach it from the item's reveal group,
            # making the original card appear empty until a later parent
            # animation restores it.
            TransformFromCopy(item.icon.copy(), destination, path_arc=-PI / 3),
            Transform(self.fill, next_fill),
            Transform(self.readout, next_readout),
            lag_ratio=0.04,
        )


class CapacityChoiceStory(VGroup):
    """Reusable story-to-math setup for bounded selection problems.

    ``beats()`` yields animations lazily, which lets capacity and stored-content
    state update only after each prior beat has been played.
    """

    def __init__(self, items, capacity, decisions=(), *,
                 problem_name="THE CAPACITY PROBLEM",
                 objective="Choose the most valuable collection that fits.",
                 opening="One container. More choices than will fit.",
                 character=None, character_label="THIEF",
                 contrast_keys=(), theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        self.problem_name_text = problem_name
        self.objective_text = objective
        self.decisions = tuple(decisions)
        self.contrast_keys = tuple(contrast_keys)

        self.character = character or ThiefCharacter(
            theme=theme, label=character_label,
        )
        self.character.scale(0.82).move_to(LEFT * 4.65 + DOWN * 0.05)
        self.bag = CapacityBag(capacity, theme=theme)
        self.bag.move_to(LEFT * 1.75 + DOWN * 0.04)

        item_mobjects = [StoryItem(spec, theme=theme) for spec in items]
        self.items = {item.spec.key: item for item in item_mobjects}
        self.item_grid = VGroup(*item_mobjects)
        columns = 2 if len(item_mobjects) > 1 else 1
        rows = math.ceil(len(item_mobjects) / columns)
        self.item_grid.arrange_in_grid(rows=rows, cols=columns, buff=(0.18, 0.18))
        self.item_grid.scale(0.82).move_to(RIGHT * 3.15 + DOWN * 0.06)

        self.problem_name = Text(
            problem_name, font_size=30, weight="BOLD", color=theme.accent,
        ).move_to(UP * 2.48)
        self.message = self._message_mobject(opening)
        self.constraint = MathTex(
            r"\max\ \text{total value}\qquad\text{subject to}\qquad"
            r"\sum\text{weights}\le C",
            color=theme.foreground,
        ).scale(0.67).move_to(DOWN * 1.70)
        self.selection_outlines = VGroup()

        self.add(
            self.character, self.bag, self.item_grid,
            self.problem_name, self.message, self.constraint,
            self.selection_outlines,
        )

    def _message_mobject(self, text, color=None):
        message = Text(text, font_size=22, color=color or self.theme.foreground)
        if message.width > 10.8:
            message.scale_to_fit_width(10.8)
        return message.move_to(DOWN * 2.66)

    def _change_message(self, text, color=None):
        # Do not morph one sentence's glyphs into another sentence.  That kind
        # of Transform produces a brief knot of overlapping letters whenever
        # the strings have different lengths.  Fade the old caption completely
        # before revealing a separate new caption instead.  Update the public
        # reference and the story's child list immediately so later beats use
        # the new sentence without depending on Transform cleanup semantics.
        old_message = self.message
        new_message = self._message_mobject(text, color)
        self.remove(old_message)
        self.add(new_message)
        self.message = new_message
        return Succession(
            FadeOut(old_message, shift=UP * 0.025),
            FadeIn(new_message, shift=UP * 0.025),
        )

    def reveal(self):
        item_reveals = [item.reveal() for item in self.items.values()]
        return AnimationGroup(
            FadeIn(self.character, shift=RIGHT * 0.22),
            self.bag.reveal_shell(),
            LaggedStart(*item_reveals, lag_ratio=0.10),
            FadeIn(self.message, shift=UP * 0.06),
            lag_ratio=0.08,
        )

    def _name_problem(self):
        return AnimationGroup(
            FadeIn(self.problem_name, shift=DOWN * 0.06),
            self._change_message(self.objective_text, self.theme.accent),
        )

    def _contrast(self):
        if len(self.contrast_keys) < 2:
            return self._change_message("Different objects trade value for space.")
        first = self.items[self.contrast_keys[0]]
        second = self.items[self.contrast_keys[1]]
        first_outline = first.frame.copy().set_fill(opacity=0).set_stroke(
            self.theme.success, width=4,
        )
        second_outline = second.frame.copy().set_fill(opacity=0).set_stroke(
            self.theme.danger, width=4,
        )
        return AnimationGroup(
            Succession(
                AnimationGroup(FadeIn(first_outline), FadeIn(second_outline)),
                AnimationGroup(FadeOut(first_outline), FadeOut(second_outline)),
            ),
            self._change_message(
                f"{first.spec.label}: small and valuable.  "
                f"{second.spec.label}: bulky and much less exciting."
            ),
        )

    def _formalize(self):
        return AnimationGroup(
            LaggedStart(
                *[item.reveal_metrics() for item in self.items.values()],
                lag_ratio=0.08,
            ),
            self.bag.reveal_capacity(),
            self._change_message("Every item has a whole-number weight and value."),
        )

    def _accept(self, decision):
        item = self.items[decision.item_key]
        outline = item.frame.copy().set_fill(opacity=0).set_stroke(
            self.theme.success, width=3,
        )
        self.selection_outlines.add(outline)
        return AnimationGroup(
            self.bag.add_item(item),
            FadeIn(outline),
            self._change_message(decision.message, self.theme.success),
        )

    def _reject(self, decision):
        item = self.items[decision.item_key]
        attempt = item.icon.copy()
        attempt.scale_to_fit_height(0.48).move_to(self.bag.body.get_center())
        cross = Cross(attempt, stroke_color=self.theme.danger, stroke_width=6)
        overflow = MathTex(
            rf"{_number(self.bag.used)}+{_number(item.spec.weight)}>"
            rf"{_number(self.bag.capacity)}",
            color=self.theme.danger,
        ).scale(0.45).next_to(self.bag.gauge_outline, RIGHT, buff=0.15)
        item_flash = item.frame.copy().set_fill(opacity=0).set_stroke(
            self.theme.danger, width=4,
        )
        bag_flash = self.bag.body.copy().set_fill(opacity=0).set_stroke(
            self.theme.danger, width=4,
        )
        attempt_sequence = Succession(
            TransformFromCopy(item.icon.copy(), attempt, path_arc=-PI / 3),
            AnimationGroup(
                Create(cross), FadeIn(overflow, shift=UP * 0.04),
                FadeIn(item_flash), FadeIn(bag_flash),
            ),
            AnimationGroup(
                FadeOut(attempt), FadeOut(cross), FadeOut(overflow),
                FadeOut(item_flash), FadeOut(bag_flash),
            ),
        )
        return AnimationGroup(
            attempt_sequence,
            self._change_message(decision.message, self.theme.danger),
        )

    def _finish_message(self):
        return self._change_message(self.objective_text, self.theme.accent)

    def _show_constraint(self):
        return FadeIn(self.constraint, shift=UP * 0.06)

    def beats(self):
        """Yield the standard story, formalization, and decision sequence."""
        yield StoryBeat(self._name_problem(), 0.72, 0.18)
        yield StoryBeat(self._contrast(), 0.90, 0.18)
        yield StoryBeat(self._formalize(), 0.90, 0.16)
        for decision in self.decisions:
            animation = (
                self._accept(decision) if decision.accepted
                else self._reject(decision)
            )
            yield StoryBeat(animation, 0.82 if decision.accepted else 1.15, 0.12)
        # Move the outgoing sentence first, then reveal the formula in its own
        # band.  Combining them makes the old text cross the new equation.
        yield StoryBeat(self._finish_message(), 0.42, 0.08)
        yield StoryBeat(self._show_constraint(), 0.62, 0.30)
