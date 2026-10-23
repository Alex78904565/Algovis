"""High-level educational-video workflows built from Algovis components."""

from dataclasses import dataclass

from manim import DOWN, FadeIn, FadeOut, LEFT, MathTex, RIGHT, Transform, VGroup

from .core.bellman import BellmanDerivation
from .core.comparison import AlgorithmComparison, RecurrenceComparison, TopDownDPBridge
from .core.correctness import InductiveProof, MonotoneCall
from .core.workflows import RecursionMemoComparison
from .presentation import SlideScene


@dataclass(frozen=True)
class BellmanSpec:
    name: str
    meaning: str
    choices: tuple[str, ...]
    decomposition: str
    recursive_decomposition: str
    refinements: tuple[str, ...]
    base_case: str
    answer: str
    population_rule: str


@dataclass(frozen=True)
class ProofSpec:
    measure: str
    base_case: str
    hypothesis: str
    step: str
    conclusion: str
    claim: str = ""


@dataclass(frozen=True)
class ComparisonSpec:
    naive: tuple[str, ...]
    memoized: tuple[str, ...]
    naive_runtime: str
    memoized_runtime: str
    naive_derivation: str = ""
    memoized_derivation: str = ""
    added_lines: tuple[int, ...] = (1, 3)
    branching_fn: object = None
    root_args: tuple = ()
    depth_limit: int = 3
    example_factory: object = None
    storage_layout: str = "grid"
    storage_axis_labels: tuple[str, str] = ("second parameter", "first parameter")
    storage_label: str = "STATE ARRAY · STORAGE VIEW"
    recursive_equation: str = ""
    array_equation: str = ""
    recursive_base_case: str = ""
    array_base_case: str = ""
    population_order_tex: str = ""


@dataclass(frozen=True)
class ProblemLesson:
    title: str
    section: str
    bellman: BellmanSpec
    monotone_expression: str
    population_order: str
    induction_measure: str
    proof_title: str
    proof: ProofSpec
    runtime_title: str
    comparison: ComparisonSpec
    monotone_bits: tuple[int, ...] | None = None
    monotone_highlight_parts: tuple[int, ...] | None = None
    top_down_state_code: str = "state"
    top_down_state_tex: str = r"\text{state}"
    dp_gain_note: str = "SUPER-EFFICIENT DP"
    intro_factory: object = None


class AlgorithmLessonScene(SlideScene):
    """A SlideScene with reusable derive/prove/compare teaching beats."""

    def show_problem_intro(self, lesson):
        """Play an optional concrete story before introducing its recurrence."""
        if lesson.intro_factory is None:
            return
        story = lesson.intro_factory(self.theme)
        self.slide_layout.body.place(story, padding=0.04)
        self.play(story.reveal(), run_time=1.20)
        for beat in story.beats():
            self.play(beat.animation, run_time=beat.run_time)
            if beat.pause_after:
                self.wait(beat.pause_after)
        self.play(self.wipe(story), run_time=0.52)
        self.remove(story)

    def show_bellman_derivation(self, title, section, spec):
        head = self.title(title, section)
        self.play(FadeIn(head))
        derivation = BellmanDerivation(
            theme=self.theme,
            name=spec.name,
            meaning=spec.meaning,
            choices=spec.choices,
            decomposition=spec.decomposition,
            recursive_decomposition=spec.recursive_decomposition,
            refinements=spec.refinements,
            base_case=spec.base_case,
            answer=spec.answer,
            population_rule=spec.population_rule,
        ).move_to(DOWN * 0.28)
        self.play(derivation.introduce())
        self.play(derivation.explain())
        self.play(derivation.explain_recursion())
        self.wait(0.55)
        self.play(derivation.reduce_long_term())
        # This is the conceptual bridge that justifies the recursive term.
        self.wait(0.8)
        self.play(derivation.consider_choices())
        self.wait(0.6)
        self.play(derivation.write_first_equation())
        while derivation.refinement_index + 1 < len(derivation.refinements):
            self.play(derivation.refine())
        finish, summary = derivation.finish()
        self.play(finish)
        self.wait(0.45)
        self.play(self.wipe(head, summary))

    def show_inductive_proof(self, title, spec):
        head = self.title(title, "Induction")
        proof = InductiveProof(theme=self.theme, **spec.__dict__).scale(0.92)
        proof.move_to(DOWN * 0.28)
        self.play(FadeIn(head), proof.reveal(), run_time=2.2)
        self.wait(0.45)
        self.play(self.wipe(head, proof))

    def show_monotone_call(self, title, lesson):
        self.show_monotone_relation(
            title, lesson.monotone_expression,
            lesson.population_order, lesson.induction_measure, lesson.monotone_bits,
            lesson.monotone_highlight_parts,
        )

    def show_monotone_relation(self, title, expression, population_order,
                               induction_measure, bit_values=None, highlight_parts=None):
        head = self.title(title, "Order and induction")
        relation = MonotoneCall(
            expression, population_order, induction_measure, bit_values=bit_values,
            highlight_parts=highlight_parts, theme=self.theme,
        ).move_to(DOWN * 0.28)
        self.play(FadeIn(head), relation.reveal(), run_time=2.0)
        self.wait(0.45)
        self.play(self.wipe(head, relation))

    def show_runtime_comparison(self, title, spec):
        head = self.title(title, "Runtime")
        if spec.branching_fn is not None:
            if spec.example_factory is not None:
                example = spec.example_factory(self.theme)
                self.slide_layout.body.place(example, padding=0.35)
                self.play(FadeIn(head), FadeIn(example), run_time=1.2)
                self.wait(0.35)
                self.play(FadeOut(example), run_time=0.45)
            visual = RecursionMemoComparison(
                spec.branching_fn, spec.root_args,
                depth_limit=spec.depth_limit, theme=self.theme,
                storage_layout=spec.storage_layout,
                axis_labels=spec.storage_axis_labels,
                graph_label=spec.storage_label,
                width=0.82, height=0.9, node_radius=0.19, label_scale=0.34,
            )
            self.play(FadeIn(head), visual.reveal_tree(), run_time=2.2)
            naive_math = None
            if spec.naive_derivation:
                naive_math = MathTex(spec.naive_derivation, color=self.theme.danger)
                naive_math.scale_to_fit_width(min(5.25, naive_math.width))
                naive_math.move_to(LEFT * 3.18 + DOWN * 3.02)
                self.play(FadeIn(naive_math, shift=DOWN * 0.06))
            # These must be separate play calls. Manim eagerly initializes
            # future introducing animations inside composite groups, exposing
            # array destinations early; overlapping both phases also makes
            # duplicate nodes blink while their edges remain.
            self.play(visual.highlight_duplicates(), run_time=0.65)
            self.play(visual.reveal_memoized(), run_time=1.25)
            memo_math = None
            if spec.memoized_derivation:
                memo_math = MathTex(spec.memoized_derivation, color=self.theme.success)
                memo_math.scale_to_fit_width(min(5.25, memo_math.width))
                memo_math.move_to(RIGHT * 3.18 + DOWN * 3.02)
                self.play(FadeIn(memo_math, shift=DOWN * 0.06))
            self.wait(0.35)
            self.play(self.wipe(
                visual, visual.arrived_cells,
                *[x for x in (naive_math, memo_math) if x is not None],
            ))
        if spec.recursive_equation and spec.array_equation:
            comparison = RecurrenceComparison(
                spec.recursive_equation, spec.array_equation,
                spec.naive_runtime, spec.memoized_runtime,
                spec.population_order_tex,
                recursive_base_tex=spec.recursive_base_case,
                array_base_tex=spec.array_base_case,
                panel_width=5.3, theme=self.theme,
            ).scale(0.82).move_to(DOWN * 0.25)
            self.reveal_recurrence_comparison(head, comparison)
        else:
            comparison = AlgorithmComparison(
                spec.naive, spec.memoized,
                spec.naive_runtime, spec.memoized_runtime,
                added_lines=spec.added_lines,
                panel_width=5.3, font_size=15, theme=self.theme,
            ).scale(0.82).move_to(DOWN * 0.25)
            self.play(FadeIn(head), comparison.reveal(), run_time=1.6)
        self.play(comparison.highlight_difference(), run_time=0.7)
        self.wait(0.4)
        self.play(self.wipe(head, comparison))

    def reveal_recurrence_comparison(self, head, comparison, *intro_animations):
        """Reveal a recurrence comparison without pre-exposing array objects.

        Keeping these as separate scene plays prevents Manim from eagerly
        initializing the eventual Bellman-array contents at the start of a
        composite animation.  A temporary equation performs the visible
        parentheses-to-brackets move, then hands off to the real array cell.
        """
        self.play(
            FadeIn(head), *intro_animations,
            FadeIn(comparison.recursive, shift=RIGHT * 0.12),
            run_time=0.8,
        )
        array_frame = VGroup(comparison.array[0], comparison.array[1])
        moving_equation = comparison.recursive.equation.copy()
        self.add(moving_equation)
        self.play(
            FadeIn(array_frame),
            Transform(moving_equation, comparison.array.equation.copy()),
            run_time=0.65,
        )
        self.remove(moving_equation)
        self.add(comparison.array.equation)
        array_details = VGroup(*comparison.array.content[1:])
        self.play(
            FadeIn(array_details),
            FadeIn(comparison.runtime_labels, shift=DOWN * 0.08),
            run_time=0.65,
        )

    def show_top_down_bridge(self, lesson):
        short_title = lesson.title.split(":", 1)[0]
        head = self.title(f"{short_title}: three small additions", "Top-down → bottom-up")
        bridge = TopDownDPBridge(
            state_code=lesson.top_down_state_code,
            state_tex=lesson.top_down_state_tex,
            population_order=lesson.population_order,
            gain_note=lesson.dp_gain_note,
            theme=self.theme,
        ).scale(0.88).move_to(DOWN * 0.20)
        self.play(FadeIn(head), bridge.reveal_recursive(), run_time=1.0)
        self.play(bridge.add_three_lines(), run_time=1.25)
        self.wait(0.25)
        # Keep each stage in its own play call.  If the hidden bottom-up group
        # shares a composite animation with the outgoing pseudocode, Manim can
        # briefly restore every hidden line while initializing the transition.
        self.play(FadeOut(bridge.panel), FadeOut(bridge.gain), run_time=0.42)
        self.play(bridge.bottom_up.animate.set_opacity(1), run_time=0.55)
        self.wait(0.35)
        self.play(FadeOut(head), FadeOut(bridge.bottom_up), run_time=0.45)
        self.remove(bridge, bridge.panel, bridge.gain, bridge.bottom_up)

    def teach_problem(self, lesson):
        """Render one complete derive → prove → compare application."""
        self.teach_solution(lesson)
        self.compare_problem(lesson)

    def teach_solution(self, lesson):
        """Render a problem's recurrence derivation and correctness proof."""
        self.show_problem_intro(lesson)
        self.show_bellman_derivation(lesson.title, lesson.section, lesson.bellman)
        self.show_monotone_call("What changes in every child call?", lesson)
        self.show_inductive_proof(lesson.proof_title, lesson.proof)

    def compare_problem(self, lesson):
        """Render a problem's naive-versus-memoized analysis."""
        self.show_runtime_comparison(lesson.runtime_title, lesson.comparison)
