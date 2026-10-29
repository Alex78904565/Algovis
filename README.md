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
from algovis import ColumnSlide, MathRow, SlideScene, SplitSlide, WARM_THEME


class FirstLesson(SlideScene):
    theme = WARM_THEME

    def construct(self):
        first = ColumnSlide('Using a definition', theme=self.theme)
        definition = first.add('definition', MathRow({
            'call': 'f(k)', 'equals': '=', 'value': r'\frac{k(k+1)}2'}))
        self.transition_to(first)
        self.wait(1)

        second = SplitSlide(first.object('title'), theme=self.theme)
        second.add('definition', definition)
        second.add('application', definition.copy(), column='right')
        second.substitute('application', call='f(3)', value=r'\frac{3(3+1)}2')
        self.transition_to(second, run_time=1.5)
        self.wait(1)

        third = second.fork().substitute('application', value='6')
        self.transition_to(third)
        self.wait(1)
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
manim -pql examples/extensible_components.py SharedCellsExample ProofExample
manim -pql examples/layout_transitions.py LayoutTransitions ProofTransitions
```

See [the component architecture](docs/COMPONENT_ARCHITECTURE.md) for the shared
cell/node hierarchy, proof objects, semantic properties, and definition-copy
helpers. Extend a shared component once to update its uses throughout a lesson.

For compositions that build in place, use `ColumnSlide`, `SplitSlide`,
`EquationSlide` or `ProofSlide` with `SlideScene.transition_to`. Share an object
to retain it, call its `copy()` to carry a new copy from the original, or fork
the layout and substitute one named equation term. See
[composition planning](docs/COMPONENT_ARCHITECTURE.md#plan-compositions-then-transition).

## Try the browser reviewer

Render the small, self-contained example and start the interface:

```bash
python review_demo.py
algovis-review --catalog examples/review/catalog.json --watch review_demo.py --watch algovis
```

Open the local address printed in the terminal. The demo has a timed example
transcript and a silent audio track; it requires no recordings or music.
Play or seek the video, select an actual Manim object, and attach a note to it.
Edit the source or click **Render section** to refresh the render and object
map while retaining the current playback position.

The **Speed** menu supports 0.5× through 3× playback and remembers your choice
across sections and reloads. Voice and background music follow the same clock.
Use **[** / **]** to change speed, **Space** to play or pause, and **← / →** to
step one second (**Shift** for ten seconds), outside text-entry controls.

Use `python -m algovis.review.server` if the `algovis-review` command is not on
your path. For your own project, copy the example catalog and provide each
section's Manim source, scene name, video, cues, and transcript. Narration and
music are optional. See [the review guide](docs/MANIM_REVIEW.md).

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

## Review the animation before rendering it

Algovis includes a small cue-driven storyboard language. It records what the
viewer should notice at each spoken phrase while leaving coordinates and
Manim implementation details out of the review.

```text
animation duplicates "Expose repeated calls":
  goal "Distinguish retained work from repeated work."
  component already_computed say "we've already computed f of 5":
    focus tree.f5_kept role=retained style=tint
    caption tree.f5_kept "already computed"
  component recompute_again say "we're computing it again":
    focus tree.f5_duplicate role=repeated style=tint
    caption tree.f5_duplicate "requested again"
```

The semantic roles keep color meaning stable across a whole lesson: `current`
is the object being discussed, `operation` is the action or relationship,
`retained` is useful finished work, and `repeated` is duplicate or discarded
work. Storyboards are validated against narration cue files before rendering.
The canonical palette mapping and pre-publish consistency checks live in
[VISUAL_LANGUAGE.md](VISUAL_LANGUAGE.md).

See [the animation-language guide](docs/ANIMATION_LANGUAGE.md) and
[animation quality standard](docs/ANIMATION_QA_STANDARD.md).

For frame-level review, Algovis can place the actual Manim-rendered MP4 beside
its full transcript. A gold tick marks each spoken trigger, while stacked
duration bars show the real Manim animations that run concurrently. A reviewer
can move among every section, click an exported Manim object (or drag around a
larger relationship), and write a plain-language correction. The saved note
keeps the cue, timestamp, object identity or normalized region, and marked frame
capture together. Source edits can rerender only the active section and refresh
the browser at the same timestamp. A separately synchronized music layer allows
the reviewer to audition narration ducking and save level/timing decisions
without baking them into the visual render. See
[the Manim review guide](docs/MANIM_REVIEW.md).

`algovis.qa.audit_project` checks a project's catalog, source methods, and
storyboard mappings. Save its report as `.review/audit.json` to expose
per-section preflight checks in the reviewer. Checks cover cues, storyboards,
density, colors, assets, and open notes. Reports identify review risks; a
rendered visual and listening pass are still needed.

Each reviewer render also writes `agent-audit.md` and `agent-audit.json` in its
section's `.review/annotations/` folder. These record actual animation intervals,
spoken word times, explicit attention triggers, and content retained or erased.
Generate an all-section index with:

```bash
python -m algovis.review.audit --catalog your-catalog.json --output .qa/animation-audit
```

Use [the agent self-review workflow](docs/ANIMATION_SELF_REVIEW.md) before
requesting a viewer's final pass. Automated findings are the agent's worklist;
they do not approve the viewer's checks.

Cue instructional motion to the exact word that introduces it. Separate named
objects should receive separate cues; a continuation such as “and so on” should
not reveal anything early. When the full equation or diagram is already on
screen, use a restrained spoken-focus cue to direct attention without removing
the surrounding context:

```python
self.wait_for_cue("capacity_term")
self.play(self.spoken_focus(recurrence[2], kind="term", trigger="capacity",
                            reason="Name the capacity term"))

self.wait_for_cue("depends_on")
self.play(self.spoken_focus(child, kind="relationship", source=parent))
```

Use `kind="term"` for a piece of a larger equation, `kind="object"` for an
already isolated node, cell, icon, or whole equation, and
`kind="relationship"` only when the narration describes a directional
connection. Actual state changes such as computed, selected, invalid, or
cached should use the theme's persistent semantic color instead of a transient
focus effect.

This repository deliberately contains no recordings, rendered video, or
third-party music. Those belong to the video project, while Algovis remains a
reusable authoring toolkit.

## Documentation

For a stable explanation layout, use `ColumnLayout` to reserve rows at their
final size and `LessonStyle` for semantic colors and consistent type sizes.
Existing scenes can opt into the same checks without moving their objects:

```python
from algovis import LessonStyle

style = LessonStyle()
style.watch("recurrence", meaning, recurrence, base_case)
style.align_rows("definition-column", meaning, recurrence, base_case)
next_call = style.math_like(current_call, "f", "(", "i+1,w", ")",
                            role="current", peers="recurrence")
```

`watch` checks declared peers at settled animation boundaries; it does not
resize them. Give intentionally different roles, such as notes or a larger
answer call, their own groups. `align_rows` checks a shared left edge without
changing geometry; travelling copies do not join that contract. `math_like`
matches the current type size, so adding a fraction or new arguments does not
require matching the height of unlike expressions. Render-time failures keep
the previous good review video available. These checks supplement visual
review of spacing, continuity, and the meaning of each cue.

The detailed component guide is in [algovis/README.md](algovis/README.md).
`library_features_demo.py` contains compact, renderable examples of the major
visual components.

## Audio helpers and development

The standalone scripts under `tools/` assemble takes, measure levels and
internal edit boundaries, master dialogue, and apply reproducible click
repairs. They retain the original recordings and check that repairs preserve
the narration timeline. The audio tools use an `assets/audio/dp/` working
folder by default; no input recordings are shipped. Optional speech cleanup
and transcription dependencies can be installed with:

```bash
python -m pip install -e ".[audio]"
```

Run the repository tests with:

```bash
python -m unittest discover -s tests -v
```

## Project status

Algovis is currently an alpha release extracted from a full dynamic-programming
video production. The API is usable, but names may continue to improve as more
lessons are built with it.

No open-source license has been selected yet. Until one is added, normal
copyright restrictions apply.
