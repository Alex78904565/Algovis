# Algovis

Algovis is a small Manim library for explaining algorithms the way you would
at a whiteboard: begin with a concrete problem, turn the choices into a
recurrence, prove it, expose the state space, and then animate the optimization.

It includes reusable components for:

- recursion trees and duplicate-state collapse animations;
- dynamic-programming arrays, dependencies, and backtracking;
- Bellman-equation derivations that move from English to mathematics;
- induction proofs and monotone recursive calls;
- weighted graphs, state spaces, pseudocode, and algorithm comparisons;
- consistent slide layouts and color themes; and
- audio-first animation timing with named narration cues.

## Installation

Algovis requires Python 3.10 or newer and Manim Community. Follow Manim's
platform setup instructions first so FFmpeg and LaTeX are available, then run:

```bash
git clone git@github.com:Alex78904565/Algovis.git
cd Algovis
python -m pip install -e .
```

## Your first scene

```python
from manim import DOWN, MathTex, Text, VGroup
from algovis import SlideScene, WARM_THEME


class FirstLesson(SlideScene):
    theme = WARM_THEME

    def construct(self):
        self.begin_slide("Start with a state", "1 · Construct")
        state = self.card(r"f(k,c)")
        meaning = Text("k items remain; c capacity remains", font_size=25)
        self.show(VGroup(state, meaning).arrange(DOWN, buff=0.35))
        self.caption("Ask what choices are possible from this state.")

        self.begin_slide("Write the recurrence", "2 · Recur")
        self.show(MathTex(
            r"f(k,c)=\max\{f(k-1,c),v_k+f(k-1,c-w_k)\}"
        ))
```

Render it with Manim:

```bash
manim -pql your_scene.py FirstLesson
```

The included examples can be rendered directly:

```bash
manim -pql slide_authoring_demo.py SlideAuthoringDemo
manim -pql library_features_demo.py TreeMemoizationDemo
manim -pql library_features_demo.py CapacityStoryDemo
```

## Audio-first timing

`NarrationTrack` makes a reviewed audio master the timing authority. Animations
refer to named cues rather than hard-coded timestamps, so a revised recording
only requires regenerating the cue file.

```python
from algovis import NarrationTrack

track = NarrationTrack.from_json("cues/introduction.json")
track.start(self)
track.wait_for(self, "introduce_state")
self.play(Write(state))
track.play_until(self, "finish_recurrence", Transform(english, equation))
track.finish(self)
```

This repository deliberately contains no recordings, rendered video, or
third-party music. Those belong to the video project, while Algovis remains a
reusable authoring toolkit.

## Documentation

The detailed component guide is in [algovis/README.md](algovis/README.md).
`library_features_demo.py` contains compact, renderable examples of the major
visual components.

## Project status

Algovis is currently an alpha release extracted from a full dynamic-programming
video production. The API is usable, but names may continue to improve as more
lessons are built with it.

No open-source license has been selected yet. Until one is added, normal
copyright restrictions apply.
