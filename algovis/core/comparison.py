from manim import *
from .pseudocode import PseudocodePanel
from ..theme import DEFAULT_SPACING, DEFAULT_THEME
from ..frames import PanelFrame
from ..semantics import SemanticProperties,set_semantics


class AlgorithmComparison(VGroup):
    """Coordinate naive and optimized pseudocode with runtime labels."""

    def __init__(self, naive_lines, optimized_lines, naive_runtime,
                 optimized_runtime, added_lines=None, titles=("Naive recursion", "Bottom-up array"),
                 panel_width=5.5, font_size=20, gap=None, accent=None,
                 theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        self.accent = accent or theme.accent
        gap = DEFAULT_SPACING.section if gap is None else gap
        self.naive = PseudocodePanel(
            naive_lines, title=titles[0], width=panel_width,
            font_size=font_size, theme=theme,
        )
        self.optimized = PseudocodePanel(
            optimized_lines, title=titles[1], width=panel_width,
            font_size=font_size, theme=theme,
        )
        self.panels = VGroup(self.naive, self.optimized).arrange(RIGHT, buff=gap, aligned_edge=UP)
        self.naive_runtime = MathTex(naive_runtime, color=theme.role_color('retained','bad')).next_to(
            self.naive, DOWN, buff=DEFAULT_SPACING.normal,
        )
        self.optimized_runtime = MathTex(optimized_runtime, color=theme.role_color('retained','good')).next_to(
            self.optimized, DOWN, buff=DEFAULT_SPACING.normal,
        )
        self.runtime_labels = VGroup(self.naive_runtime, self.optimized_runtime)
        set_semantics(self.naive_runtime,SemanticProperties(status='computed',evaluation='bad'),theme=theme)
        set_semantics(self.optimized_runtime,SemanticProperties(status='computed',evaluation='good'),theme=theme)
        self.added_lines = list(added_lines or [])
        self.add(self.panels, self.runtime_labels)

        for index, line in enumerate(self.naive.lines):
            line.set_opacity(0.56)
        for index, line in enumerate(self.optimized.lines):
            line.set_opacity(1 if index in self.added_lines else 0.56)
            if index in self.added_lines:
                line.set_color(self.accent)

    def reveal(self):
        """Reveal both comparable panels without exposing later subanimations."""
        return Succession(
            AnimationGroup(
                FadeIn(self.naive, shift=RIGHT * 0.12),
                FadeIn(self.optimized, shift=LEFT * 0.12),
                lag_ratio=0.35,
            ),
            FadeIn(self.runtime_labels, shift=UP * 0.10),
        )

    def highlight_difference(self):
        return AnimationGroup(*[
            Indicate(self.optimized.lines[index], color=self.accent)
            for index in self.added_lines
        ], lag_ratio=0.18)

    def step(self, naive_line=None, optimized_line=None, *animations):
        parts = list(animations)
        if naive_line is not None:
            parts.append(self.naive.highlight_line(naive_line, color=self.theme.primary))
        if optimized_line is not None:
            parts.append(self.optimized.highlight_line(optimized_line, color=self.theme.primary))
        return AnimationGroup(*parts)


class RecurrenceComparison(VGroup):
    """Compare one recursive recurrence with its bottom-up array form.

    The two panels deliberately differ as little as possible: function-call
    parentheses become state-array brackets. Population order is displayed as
    the one additional requirement for evaluating the array bottom-up.
    """

    def __init__(self, recursive_tex, array_tex, naive_runtime, optimized_runtime,
                 population_order_tex, recursive_base_tex="", array_base_tex="",
                 panel_width=5.45, equation_scale=0.78,
                 titles=("Recursive function definition", "Bottom-up Bellman array"),
                 accent=None, theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        self.accent = accent or theme.accent

        def make_panel(tex, title, color, population=None, base_case=None):
            equation = MathTex(tex, color=theme.foreground).scale(equation_scale)
            equation.scale_to_fit_width(min(panel_width - 0.55, equation.width))
            content = VGroup(equation)
            if base_case:
                base = MathTex(base_case, color=theme.success).scale(0.62)
                base.scale_to_fit_width(min(panel_width - 0.55, base.width))
                content.add(base)
            if population:
                order = MathTex(population, color=theme.success).scale(0.60)
                order.scale_to_fit_width(min(panel_width - 0.55, order.width))
                content.add(order)
            content.arrange(DOWN, buff=DEFAULT_SPACING.normal)
            background = PanelFrame(panel_width, max(1.75, content.height + 0.95), theme=theme)
            content.move_to(background).shift(DOWN * 0.08)
            heading = background.heading(title)
            panel = VGroup(background, heading, content)
            panel.equation = equation
            panel.content = content
            return panel

        self.recursive = make_panel(
            recursive_tex, titles[0], theme.primary, base_case=recursive_base_tex,
        )
        self.array = make_panel(
            array_tex, titles[1], theme.primary,
            population=population_order_tex, base_case=array_base_tex,
        )
        self.panels = VGroup(self.recursive, self.array).arrange(
            RIGHT, buff=DEFAULT_SPACING.section, aligned_edge=UP,
        )
        self.naive_runtime = MathTex(naive_runtime, color=theme.role_color('retained','bad')).next_to(
            self.recursive, DOWN, buff=DEFAULT_SPACING.normal,
        )
        self.optimized_runtime = MathTex(optimized_runtime, color=theme.role_color('retained','good')).next_to(
            self.array, DOWN, buff=DEFAULT_SPACING.normal,
        )
        self.runtime_labels = VGroup(self.naive_runtime, self.optimized_runtime)
        set_semantics(self.naive_runtime,SemanticProperties(status='computed',evaluation='bad'),theme=theme)
        set_semantics(self.optimized_runtime,SemanticProperties(status='computed',evaluation='good'),theme=theme)
        self.add(self.panels, self.runtime_labels)

    def reveal(self):
        return Succession(
            FadeIn(self.recursive, shift=RIGHT * 0.12),
            AnimationGroup(
                FadeIn(VGroup(self.array[0], self.array[1])),
                TransformFromCopy(self.recursive.equation, self.array.equation),
            ),
            FadeIn(self.array.content),
            FadeIn(self.runtime_labels, shift=UP * 0.10),
        )

    def highlight_difference(self):
        return Indicate(self.array.equation, color=self.accent, scale_factor=1.03)


class TopDownDPBridge(VGroup):
    """Show the three additions that turn brute-force recursion into top-down DP.

    The second beat converts the same state notation to a bottom-up array and
    states the required population order.
    """

    def __init__(self, state_code="state", state_tex=r"\text{state}",
                 population_order="dependencies before users",
                 gain_note="SUPER-EFFICIENT DP", panel_width=8.3,
                 theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        lines = (
            "answer = array filled with UNKNOWN",
            f"solve({state_code}):",
            f"  if known(answer[{state_code}]): return answer[{state_code}]",
            "  result = recurrence",
            f"  answer[{state_code}] = result",
            "  return result",
        )
        self.added_lines = (0, 2, 4)
        self.panel = PseudocodePanel(
            lines, title="THREE SMALL ADDITIONS", width=panel_width,
            font_size=17, theme=theme,
        )
        for index, line in enumerate(self.panel.lines):
            if index in self.added_lines:
                line.set_color(theme.accent).set_opacity(0)

        self.gain = VGroup(
            Text(gain_note, font_size=22, color=theme.foreground),
            Text(
                "each reachable state is evaluated once",
                font_size=18, color=theme.success,
            ),
        ).arrange(DOWN, buff=0.20).next_to(
            self.panel, DOWN, buff=DEFAULT_SPACING.normal,
        )
        self.gain.scale_to_fit_width(min(panel_width, self.gain.width))
        self.gain.set_opacity(0)

        self.array_equation = MathTex(
            rf"f({state_tex})\longrightarrow f[{state_tex}]",
            color=theme.foreground,
        ).scale(0.95)
        order_value = Text(population_order, font_size=21, color=theme.primary)
        order_value.scale_to_fit_width(min(panel_width, order_value.width))
        self.order = VGroup(
            Text("POPULATION ORDER", font_size=15, color=theme.muted), order_value,
        ).arrange(DOWN, buff=DEFAULT_SPACING.tight)
        self.bottom_up = VGroup(
            Text("BOTTOM-UP ARRAY", font_size=19, color=theme.foreground),
            self.array_equation, self.order,
        ).arrange(DOWN, buff=DEFAULT_SPACING.normal)
        self.bottom_up.move_to(self.panel)
        self.bottom_up.set_opacity(0)
        self.add(self.panel, self.gain, self.bottom_up)

    def reveal_recursive(self):
        return FadeIn(self.panel, shift=UP * 0.08)

    def add_three_lines(self):
        additions = [
            self.panel.lines[index].animate.set_opacity(1)
            for index in self.added_lines
        ]
        return Succession(
            LaggedStart(*additions, lag_ratio=0.28),
            self.gain.animate.set_opacity(1),
        )

    def reveal_bottom_up(self):
        return AnimationGroup(
            FadeOut(self.panel), FadeOut(self.gain),
            self.bottom_up.animate.set_opacity(1),
        )
