"""Reusable inductive-correctness proof visuals."""
import textwrap

from manim import (
    Create, DOWN, FadeIn, LaggedStart, LEFT, MathTex,
    SurroundingRectangle, Text, VGroup,
)

from ..theme import DEFAULT_SPACING, DEFAULT_THEME
from ..frames import ProofFrame
from .proof import Proof
from .state_space import BinaryStateVector


class InductiveProof(Proof):
    """A compact base/hypothesis/step proof for a recursive algorithm."""

    def __init__(self, *, measure, base_case, hypothesis, step, conclusion,
                 claim="",
                 theme=DEFAULT_THEME, width=11.5, **kwargs):
        super().__init__(theme=theme,**kwargs)
        entries = [
            ("DEFINITIONS", measure, theme.foreground),
            ("CLAIM", claim or conclusion, theme.foreground),
            ("BASE CASE", base_case, theme.success),
            ("INDUCTION HYPOTHESIS", hypothesis, theme.foreground),
            ("INDUCTIVE STEP", step, theme.foreground),
        ]
        for label, body, color in entries:
            explanation = Text(body, font_size=21, color=color)
            # Wrap words at the same type size instead of shrinking a long row.
            line_length = len(body)
            while explanation.width > min(width, 9.6) and line_length > 1:
                line_length -= 1
                explanation = Text(textwrap.fill(body, width=line_length), font_size=21, color=color)
            if explanation.width > min(width, 9.6):
                raise ValueError("Proof text exceeds its content column")
            self.add_row(label,explanation)
        self.conclusion = self.frame.place("conclusion",Text(conclusion,font_size=21,color=theme.success))
        self.rows.add(self.conclusion)

    def reveal(self, lag_ratio=0.16):
        from manim import AnimationGroup
        return AnimationGroup(Create(self.frame.divider),
            LaggedStart(*[FadeIn(row, shift=DOWN * 0.05) for row in self.rows],
                        lag_ratio=lag_ratio))


class MonotoneCall(VGroup):
    """Connect a child-call dependency to population order and induction."""

    def __init__(self, expression, population_order, induction_measure,
                 theme=DEFAULT_THEME, bit_values=None, highlight_parts=None, **kwargs):
        super().__init__(**kwargs)
        prompt = Text("WHAT CHANGES STRICTLY IN EVERY CHILD CALL?",
                      font_size=15, color=theme.muted)
        expression_parts = (expression,) if isinstance(expression, str) else tuple(expression)
        self.expression = MathTex(*expression_parts, color=theme.foreground)
        indices = tuple(highlight_parts or range(len(expression_parts)))
        # Separate boxes make the actual changing arguments explicit.  A
        # single rectangle around disjoint parent/child parts misleadingly
        # encloses everything between them.
        self.boxes = VGroup(*[
            SurroundingRectangle(self.expression[index], color=theme.accent, buff=0.08)
            for index in indices
        ])
        order_label = Text("BOTTOM-UP ORDER", font_size=14, color=theme.muted)
        order = Text(population_order, font_size=22, color=theme.success)
        measure_label = Text("INDUCTION MEASURE", font_size=14, color=theme.muted)
        measure = Text(induction_measure, font_size=22, color=theme.primary)
        order_group = VGroup(order_label, order).arrange(
            DOWN, aligned_edge=LEFT, buff=DEFAULT_SPACING.tight,
        )
        measure_group = VGroup(measure_label, measure).arrange(
            DOWN, aligned_edge=LEFT, buff=DEFAULT_SPACING.tight,
        )
        expression_group = VGroup(self.expression, self.boxes)
        self.bits = None
        if bit_values is not None:
            labels = [f"v_{i + 1}" for i in range(len(bit_values))]
            self.bits = BinaryStateVector(
                labels, list(bit_values), theme=theme,
            ).scale(0.62)
            expression_group = VGroup(expression_group, self.bits).arrange(DOWN, buff=0.22)
        self.rows = VGroup(prompt, expression_group, order_group, measure_group)
        self.rows.arrange(DOWN, buff=0.38, aligned_edge=LEFT)
        if self.rows.width > 11.2:
            self.rows.scale_to_fit_width(11.2)
        self.add(self.rows)

    def reveal(self):
        reveal = LaggedStart(
            FadeIn(self.rows[0]), FadeIn(self.expression),
            LaggedStart(*[Create(box) for box in self.boxes], lag_ratio=0.2),
            *([] if self.bits is None else [FadeIn(self.bits)]),
            FadeIn(self.rows[2]), FadeIn(self.rows[3]), lag_ratio=0.18,
        )
        if self.bits is None:
            return reveal
        first_zero = next(i for i, parameter in enumerate(self.bits.parameters)
                          if parameter.value == 0)
        from manim import Succession
        return Succession(reveal, self.bits.flip(first_zero))
