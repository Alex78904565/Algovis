"""A self-contained, silent example of the transcript-based Manim reviewer.

Run ``python review_demo.py`` to render the video and selectable object map.
Then run ``algovis-review --catalog examples/review/catalog.json``.
"""
import os
from pathlib import Path
import subprocess
import sys
import wave

from manim import DOWN, FadeIn, FadeOut, RIGHT, RoundedRectangle, Text, UP, VGroup
from algovis import SlideScene

ROOT = Path(__file__).resolve().parent


class ReviewDemo(SlideScene):
    def construct(self):
        silence = ROOT / ".review" / "demo" / "silence.wav"
        silence.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(silence), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(48000)
            audio.writeframes(b"\0\0" * 48000 * 9)
        self.begin_narration(ROOT / "examples/review/cues.json", project_root=ROOT)

        title = Text("Store each answer once", font_size=38, color=self.theme.primary)
        title.move_to(UP * 2.3)

        def state_card():
            box = RoundedRectangle(width=2.0, height=1.0, corner_radius=.12,
                                   color=self.theme.primary,
                                   fill_color=self.theme.surface, fill_opacity=1)
            label = Text("f(4)", font_size=30, color=self.theme.foreground)
            return VGroup(box, label)

        retained, repeated = state_card(), state_card()
        VGroup(retained, repeated).arrange(RIGHT, buff=1.8)
        known = Text("already computed", font_size=23, color=self.theme.success)
        known.next_to(retained, DOWN, buff=.3)
        again = Text("requested again", font_size=23, color=self.theme.danger)
        again.next_to(repeated, DOWN, buff=.3)

        self.wait_for_cue("section_start")
        self.play(FadeIn(title), FadeIn(retained), run_time=.6)
        self.wait_for_cue("duplicate")
        self.play(FadeIn(repeated), run_time=.5)
        self.wait_for_cue("compare")
        self.play(
            retained[0].animate.set_stroke(self.theme.success).set_fill(self.theme.success, opacity=.18),
            repeated[0].animate.set_stroke(self.theme.danger).set_fill(self.theme.danger, opacity=.18),
            FadeIn(known), FadeIn(again), run_time=.6,
        )
        self.wait_for_cue("share")
        self.play(FadeOut(again), repeated.animate.move_to(retained), run_time=.7)
        self.play(FadeOut(repeated), run_time=.25)
        self.wait_for_cue("section_end")
        self.play(FadeOut(title), FadeOut(retained), FadeOut(known), run_time=.4)
        self.finish_narration()


if __name__ == "__main__":
    subprocess.run(
        [sys.executable, "-m", "manim", "-ql", str(Path(__file__).resolve()), "ReviewDemo"],
        cwd=ROOT, check=True,
        env={**os.environ, "ALGOVIS_REVIEW_MANIFEST":
             str(ROOT / ".review/manifests/review_demo.objects.json")},
    )
