from manim import *
from algovis import (
    ApplyFunction,
    DPTable,
    Function,
    InductionStep,
    MonotonicVisualizer,
    NodeState,
    PanelLayout,
    RecursiveTree,
    SmartBulletedList,
)

class AlgovisDemo(Scene):
    def construct(self):
        layout = PanelLayout()
        self.camera.background_color = "#0B1020"

        def section_title(text):
            return Text(text, font_size=30, weight=MEDIUM, color=BLUE_B).to_edge(UP, buff=0.35)

        def clear(*mobjects):
            return AnimationGroup(*[FadeOut(mob, shift=DOWN * 0.12) for mob in mobjects], lag_ratio=0.06)

        # 1. Introduction - Bulleted List
        title = Text("Algovis", font_size=58, weight=BOLD, color=BLUE_B).shift(UP * 1.15)
        subtitle = Text("Visual building blocks for algorithms", font_size=27, color=GREY_B).next_to(title, DOWN)
        bullets = SmartBulletedList(
            "Proof-Centric Recursion",
            "Monotonic Induction Visuals",
            "State-Aware Trees",
            "Dynamic Substitution"
        ).scale(0.72).next_to(subtitle, DOWN, buff=0.7)

        self.play(Write(title), FadeIn(subtitle, shift=UP * 0.15))
        self.play(LaggedStart(*[FadeIn(item, shift=RIGHT * 0.2) for item in bullets.items], lag_ratio=0.12))
        self.wait(1)
        self.play(clear(title, subtitle, bullets))

        # 2. Function Application & Substitution
        heading = section_title("Function application")
        func = Function("f", "n", "f(n-1) + f(n-2)").scale(1.12).move_to(UP * 0.65)
        param = MathTex("5", color=YELLOW).scale(1.25).move_to(DOWN * 1.05)

        self.play(FadeIn(heading, shift=DOWN * 0.15), Write(func))
        self.play(Write(param))
        self.wait(1)

        # Highlight parameter and apply
        self.play(ApplyFunction(func, param))
        self.wait(1)

        # CLEAR SCENE BEFORE TREE
        # ``ApplyFunction`` has already removed the argument.  Fading it a
        # second time would briefly add it back to the scene.
        self.play(clear(heading, func))

        # 3. Recursive Tree with State Management
        def fib_branch(n):
            if n <= 1: return str(n), []
            return f"f({n})", [(n-1,), (n-2,)]

        # Position tree relative to frame, avoiding overlap with header
        heading = section_title("Recursive call tree")
        tree = RecursiveTree(fib_branch, (3,), depth_limit=3, width=1.35, height=1.25)
        tree.scale_to_fit_height(5.55).move_to(DOWN * 0.25)

        self.play(FadeIn(heading, shift=DOWN * 0.15))
        self.play(tree.get_unroll_anim(lag_ratio=0.25), run_time=3)
        self.wait(1)

        # Animate state changes (Call/Return)
        root_node = tree.tree_structure
        self.play(tree.get_set_state_anim(root_node, NodeState.ACTIVE))
        self.wait(0.5)
        self.play(tree.get_set_state_anim(root_node, NodeState.RESOLVED))
        self.wait(1)

        # CLEAR SCENE BEFORE INDUCTION
        self.play(clear(heading, tree))

        # 4. Induction & Monotonicity
        heading = section_title("Induction step")
        mono = MonotonicVisualizer(start_val=5, end_val=0, label="n").move_to(UP * 1.15)
        pk = MathTex("P(k):", "f(k)=k")
        pk1 = MathTex("P(k+1):", "f(k+1)=k+1")
        pk[0].set_color(BLUE_B)
        pk1[0].set_color(BLUE_B)
        statements = VGroup(pk, pk1).arrange(
            RIGHT, buff=2.0, aligned_edge=DOWN
        ).move_to(DOWN * 1.25)

        self.play(FadeIn(heading, shift=DOWN * 0.15), FadeIn(mono))
        self.play(Write(pk))
        self.play(InductionStep(pk, pk1, monotonic_vis=mono, next_val=4))
        self.wait(1)

        # CLEAR SCENE BEFORE DP
        self.play(clear(heading, pk, pk1, mono))

        # 5. DP Tables & Dependencies
        heading = section_title("Dynamic-programming dependencies")
        table = DPTable(rows=4, cols=4, cell_width=1.2, cell_height=0.72).move_to(DOWN * 0.2)
        target = table.get_cell(2, 2)
        deps = [table.get_cell(1, 2), table.get_cell(1, 1)]

        self.play(FadeIn(heading, shift=DOWN * 0.15), FadeIn(table))
        self.play(table.highlight_dependency(target, deps))
        self.wait(2)
        self.play(clear(heading, table))
