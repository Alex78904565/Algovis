"""Small renderable examples for the reusable Algovis components."""

from manim import *
from algovis import (
    AlgorithmComparison,
    BinaryStateVector,
    CapacityChoiceStory,
    DEFAULT_THEME,
    DecisionFanout,
    DPTable,
    DPWorkflow,
    GraphVis,
    PseudocodePanel,
    StateSpaceVisualizer,
    StoryDecision,
    StoryItemSpec,
    RecursiveTree,
)


class TableWorkflowDemo(Scene):
    def construct(self):
        self.camera.background_color = "#0B1020"
        table = DPTable(
            3, 5,
            row_labels=["i=0", "i=1", "i=2"],
            col_labels=["0", "1", "2", "3", "4"],
            cell_width=0.75,
            cell_height=0.55,
        ).shift(LEFT * 2.3)
        code = PseudocodePanel([
            "for item in items:",
            "  for capacity in range(C):",
            "    dp[i][c] = best choice",
            "recover chosen items",
        ], font_size=17, width=4.7).scale(0.82).shift(RIGHT * 3.6)
        self.add(table, code)
        workflow = DPWorkflow(table, code)
        steps = [
            {"cell": (0, 0), "value": "0", "code_line": 0},
            {"cell": (1, 1), "value": "3", "code_line": 2,
             "dependencies": [(0, 0)], "dependency_labels": ["take"]},
            {"cell": (2, 3), "value": "7", "code_line": 2,
             "dependencies": [(1, 1)], "dependency_labels": ["take"]},
        ]
        self.play(workflow.population_animation(steps), run_time=3)
        self.play(workflow.recovery_animation([(2, 3), (1, 1), (0, 0)], code_line=3), run_time=2)
        self.wait(0.3)


class StateSpaceDemo(Scene):
    def construct(self):
        self.camera.background_color = "#0B1020"
        intervals = StateSpaceVisualizer.intervals(
            5, columns=5, title="Contiguous intervals (i,j)"
        ).scale(0.82).to_edge(LEFT)
        subsets = StateSpaceVisualizer.subsets(
            range(4), columns=4, title="Arbitrary subsets"
        ).scale(0.72).to_edge(RIGHT)
        interval_count = intervals.count_label(r"\Theta(n^2)")
        subset_count = subsets.count_label(r"2^n")
        self.play(FadeIn(intervals), FadeIn(subsets))
        self.play(Write(interval_count), Write(subset_count))
        self.play(intervals.highlight_state((1, 4)), subsets.highlight_state(frozenset({0, 2})))
        self.wait(0.3)


class WeightedGraphDemo(Scene):
    def construct(self):
        self.camera.background_color = "#0B1020"
        graph = GraphVis(
            ["A", "B", "C", "D"],
            [("A", "B", 4), ("B", "C", 2), ("C", "D", 5),
             ("D", "A", 3), ("A", "C", 7)],
            layout="circular",
        )
        self.play(FadeIn(graph))
        self.play(graph.traverse_path(["A", "B", "C", "D"]), run_time=2.5)
        self.wait(0.3)


class TreeMemoizationDemo(Scene):
    def construct(self):
        self.camera.background_color = "#0B1020"
        def branch(n):
            return f"f({n})", [] if n <= 2 else [(n - 1,), (n - 2,)]
        tree = RecursiveTree(branch, (6,), depth_limit=4, width=0.85, height=0.9,
                             node_radius=0.23, label_scale=0.42)
        tree.scale_to_fit_height(5.8)
        self.play(tree.get_unroll_anim(lag_ratio=0.08), run_time=2)
        self.play(tree.highlight_duplicates(), run_time=1)
        duplicate = next(iter(tree.get_duplicate_groups().values()))[1]
        self.play(tree.show_cache_hit(duplicate))
        kept = [
            nodes[0]
            for nodes in tree.get_duplicate_groups(include_singletons=True).values()
        ]
        self.play(tree.collapse_to_backbone(kept), run_time=2.5)
        self.play(tree.collapse_to_state_graph(), run_time=2)
        self.wait(0.3)


class ComparisonDemo(Scene):
    def construct(self):
        self.camera.background_color = "#0B1020"
        naive = ["fib(n):", "  if n <= 2: return 1",
                 "  return fib(n-1) + fib(n-2)"]
        memo = ["fib(n):", "  if n in memo: return memo[n]",
                "  if n <= 2: return 1", "  answer = fib(n-1) + fib(n-2)",
                "  memo[n] = answer", "  return answer"]
        comparison = AlgorithmComparison(
            naive, memo, r"\Omega(1.6^n)", r"O(n)",
            added_lines=[1, 4], panel_width=5.5, font_size=17,
        ).scale(0.9)
        self.play(comparison.reveal(), run_time=3)
        self.play(comparison.highlight_difference())
        self.wait(0.3)


class DecisionAndParametersDemo(Scene):
    def construct(self):
        self.camera.background_color = "#0B1020"
        state = VGroup(RoundedRectangle(width=1.5, height=0.6, corner_radius=0.08),
                       MathTex("(k,t)").scale(0.55))
        fanout = DecisionFanout(state, [
            {"label": "buy 0", "target": "t-g"},
            {"label": "buy 1", "target": "t+1-g"},
            {"label": "buy 2", "target": "t+2-g", "enabled": False},
        ], optimizer="min").scale(0.8).to_edge(LEFT, buff=0.5)
        bits = BinaryStateVector(["v_1", "v_2", "v_3", "v_4"], [1, 0, 0, 0])
        bits.scale(0.8).to_edge(RIGHT, buff=0.5)
        self.play(fanout.grow(), FadeIn(bits), run_time=2.5)
        self.play(fanout.set_choice_enabled(2, True), bits.flip(2))
        self.play(fanout.choose(1), bits.show_bounds(), run_time=1.5)
        self.wait(0.3)


class CapacityStoryDemo(Scene):
    """Introduce a bounded-choice problem in pictures before using notation."""

    def construct(self):
        DEFAULT_THEME.apply(self)
        story = CapacityChoiceStory(
            items=(
                StoryItemSpec("gem", "diamond", 1, 10, icon="jewelry"),
                StoryItemSpec("laptop", "laptop", 2, 7, icon="laptop"),
                StoryItemSpec("roll", "toilet paper", 3, 1,
                              icon="toilet_paper"),
            ),
            capacity=3,
            decisions=(
                StoryDecision("gem", True, "The diamond fits easily."),
                StoryDecision("laptop", True, "The laptop fills the bag."),
                StoryDecision("roll", False, "The toilet paper would overflow it."),
            ),
            contrast_keys=("gem", "roll"),
            theme=DEFAULT_THEME,
        ).scale(0.92)
        self.play(story.reveal(), run_time=1.2)
        for beat in story.beats():
            self.play(beat.animation, run_time=beat.run_time)
            self.wait(beat.pause_after)
        self.wait(0.3)
