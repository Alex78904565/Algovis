"""A minimal hand-authored Algovis video using the presentation layer."""

from manim import DOWN, MathTex, Text, VGroup
from algovis import SlideScene, WARM_THEME


class SlideAuthoringDemo(SlideScene):
    theme = WARM_THEME

    def construct(self):
        slide = self.begin_slide("Start with a state", "1 · Construct")
        state = self.card(r"f(k,c)")
        meaning = Text("k items remain; c capacity remains", font_size=25)
        self.show(VGroup(state, meaning).arrange(DOWN, buff=0.35))
        self.caption("Ask what choices are possible from this state.")

        slide = self.begin_slide("Write the recurrence", "2 · Recur")
        recurrence = MathTex(
            r"f(k,c)=\max\{f(k-1,c),v_k+f(k-1,c-w_k)\}"
        )
        self.show(recurrence)
        self.caption("Then choose a base case and the initial call.")
