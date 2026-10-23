from manim import *

class MonotonicVisualizer(VGroup):
    """
    Visualizes a value that changes monotonically (e.g., recursion depth, n in f(n)).
    """
    def __init__(self, start_val, end_val, label="n", width=4, **kwargs):
        super().__init__(**kwargs)
        self.current_val = start_val
        self.end_val = end_val

        self.axis = NumberLine(
            x_range=[min(start_val, end_val), max(start_val, end_val), 1],
            length=width,
            include_numbers=True,
            label_direction=DOWN
        )
        self.pointer = Triangle(
            color=YELLOW,
            fill_color=YELLOW,
            fill_opacity=0.85,
            stroke_width=2,
        ).scale(0.14).rotate(PI)
        self.pointer.next_to(self.axis.n2p(start_val), UP, buff=0.06)

        self.label = MathTex(label).scale(0.72).next_to(self.pointer, UP, buff=0.1)

        self.add(self.axis, self.pointer, self.label)

    def update_to(self, new_val):
        """Returns an animation to move the pointer to a new value"""
        self.current_val = new_val
        destination = self.axis.n2p(new_val)
        pointer_target = self.pointer.copy().next_to(destination, UP, buff=0.06)
        label_target = self.label.copy().next_to(pointer_target, UP, buff=0.1)
        return AnimationGroup(
            self.pointer.animate.move_to(pointer_target),
            self.label.animate.move_to(label_target),
            lag_ratio=0,
        )

class InductionStep(Succession):
    """
    Animates the logical bridge from P(k) to P(k+1).
    """
    def __init__(self, pk_tex, pk1_tex, monotonic_vis=None, next_val=None, **kwargs):
        anims = []

        # 1. Highlight P(k)
        box_k = SurroundingRectangle(pk_tex, color=BLUE_B, buff=0.16, stroke_width=2)
        anims.append(Create(box_k))

        # 2. Update monotonic property if provided
        if monotonic_vis and next_val is not None:
            anims.append(monotonic_vis.update_to(next_val))

        # 3. Show P(k+1) emerging from P(k)
        # A typeset implication sits on the same visual baseline as the math.
        # A geometric Arrow aligns to bounding boxes and tends to look low or
        # high when the two expressions have different ascenders.
        arrow = MathTex(r"\Longrightarrow", color=BLUE_B).scale(0.82)
        arrow.move_to((pk_tex.get_right() + pk1_tex.get_left()) / 2)
        anims.append(Write(arrow))
        anims.append(FadeIn(pk1_tex, shift=RIGHT * 0.18))

        # 4. Cleanup
        anims.append(Wait(0.35))
        anims.append(AnimationGroup(Uncreate(box_k), FadeOut(arrow), lag_ratio=0))

        super().__init__(*anims, **kwargs)
