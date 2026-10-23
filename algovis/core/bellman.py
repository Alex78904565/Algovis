"""Step-by-step Bellman-equation derivations."""

from manim import (
    AnimationGroup, Brace, DOWN, FadeIn, FadeOut, FadeTransform, LEFT, MathTex,
    RIGHT, Succession, Text, UP, VGroup,
)

from ..theme import DEFAULT_SPACING, DEFAULT_THEME


class BellmanDerivation:
    """A storyboard helper that lets state emerge from refined choices.

    The object deliberately tracks separate display phases instead of being a
    nested VGroup. This makes it safe to replace an English equation with its
    mathematical refinements while writing a scene by hand.
    """

    QUESTIONS = {
        "meaning": "What does this function represent?",
        "choices": "What choices can I make?",
        "recursion": "What is the total effect of one choice?",
        "base": "What is the simplest instance?",
        "answer": "How does this function give the answer the problem asks for?",
        "order": "What changes strictly in every child call?",
    }

    def __init__(self, *, name, meaning, choices, decomposition,
                 recursive_decomposition, refinements, base_case,
                 answer=None, initial_call=None, population_rule, theme=DEFAULT_THEME,
                 width=11.5):
        self.theme = theme
        self.width = width
        self.name = self._prompt("Let's name the answer", MathTex(name, color=theme.foreground))
        # Keep the function visible while its English alternatives are being
        # discovered.  The choices are the right-hand side of the equation,
        # not a temporary slide that replaces it.
        lhs_tex = name.split("=", 1)[0].strip() + "="
        meaning_equation = VGroup(
            MathTex(lhs_tex, color=theme.foreground),
            Text(meaning, font_size=23, color=theme.foreground),
        ).arrange(RIGHT, buff=DEFAULT_SPACING.normal)
        self.meaning = self._prompt(self.QUESTIONS["meaning"], meaning_equation)
        choice_lines = VGroup(*[
            Text(choice, font_size=22, color=theme.foreground)
            for choice in choices
        ]).arrange(DOWN, aligned_edge=LEFT, buff=DEFAULT_SPACING.normal)
        choice_brace = Brace(choice_lines, LEFT, color=theme.foreground)
        lhs = MathTex(lhs_tex, color=theme.foreground)
        lhs.next_to(choice_brace, LEFT, buff=DEFAULT_SPACING.tight)
        english_equation = VGroup(lhs, choice_brace, choice_lines)
        self.choices = self._prompt(self.QUESTIONS["choices"], english_equation)
        self.decomposition = self._prompt(
            self.QUESTIONS["recursion"], MathTex(decomposition, color=theme.foreground)
        )
        self.recursive_decomposition = self._prompt(
            "What is the long-term value?",
            MathTex(recursive_decomposition, color=theme.foreground),
        )
        self.refinements = [MathTex(tex, color=theme.foreground) for tex in refinements]
        for equation in self.refinements:
            equation.scale_to_fit_width(min(width, equation.width))
        self.equation = self.refinements[0]
        self.refinement_index = 0
        self.base = self._prompt(self.QUESTIONS["base"], MathTex(base_case, color=theme.success))
        answer_expression = answer if answer is not None else initial_call
        if answer_expression is None:
            raise ValueError("BellmanDerivation requires an answer expression.")
        self.answer = self._prompt(
            self.QUESTIONS["answer"], MathTex(answer_expression, color=theme.accent)
        )
        self.order = self._prompt(
            self.QUESTIONS["order"], Text(population_rule, font_size=22, color=theme.primary)
        )
        self.anchor = None

    def _prompt(self, question, answer):
        question_mob = Text(question.upper(), font_size=15, color=self.theme.muted)
        group = VGroup(question_mob, answer).arrange(
            DOWN, aligned_edge=LEFT, buff=DEFAULT_SPACING.tight,
        )
        if group.width > self.width:
            group.scale_to_fit_width(self.width)
        return group

    def introduce(self):
        return AnimationGroup(FadeIn(self.name), lag_ratio=0)

    def explain(self):
        return FadeTransform(self.name, self.meaning)

    def consider_choices(self):
        return FadeTransform(self.recursive_decomposition, self.choices)

    def explain_recursion(self):
        return FadeTransform(self.meaning, self.decomposition)

    def reduce_long_term(self):
        return FadeTransform(self.decomposition, self.recursive_decomposition)

    def write_first_equation(self):
        return FadeTransform(self.choices, self.equation)

    def refine(self):
        if self.refinement_index + 1 >= len(self.refinements):
            raise IndexError("The Bellman derivation has no remaining refinement.")
        target = self.refinements[self.refinement_index + 1]
        animation = FadeTransform(self.equation, target)
        self.equation = target
        self.refinement_index += 1
        return animation

    def move_to(self, point):
        """Set one stable position for every mutually exclusive phase."""
        self.anchor = point
        for phase in [self.name, self.meaning, self.choices, self.decomposition,
                      self.recursive_decomposition, *self.refinements,
                      self.base, self.answer, self.order]:
            phase.move_to(point)
        return self

    def finish(self):
        """Replace the final equation with base, answer, and order prompts."""
        summary = VGroup(self.base, self.answer, self.order).arrange(
            DOWN, aligned_edge=LEFT, buff=DEFAULT_SPACING.relaxed,
        )
        if summary.width > self.width:
            summary.scale_to_fit_width(self.width)
        if self.anchor is not None:
            summary.move_to(self.anchor)
        return Succession(FadeOut(self.equation), FadeIn(summary)), summary
