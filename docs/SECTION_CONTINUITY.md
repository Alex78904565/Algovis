# Rendering a continuous lesson as separate clips

Separate rendering is an iteration tool. It must not introduce a new blank page
between two sentences that belong to the same explanation.

The last visible frame of a section is the next section's starting composition.
Build both sides from the same factory when the next section continues editing
an array, tree, proof, or equation. Keep values, positions, type sizes and colors
identical across the cut. Populate an empty introductory row only when its values
are spoken in the following section. A chapter marker may change deliberately.

For a genuine change of topic, carry the previous composition across the cut,
then clear it before revealing the new topic. Do this in the existing opening
animation's time slot. Do not add preroll that offsets the narration, crossfade
unrelated equations, or clear useful work just to recreate it immediately.

## Native artwork handoffs

`SectionHandoff` saves painted paths, images, their hierarchy, and selection
labels as data-only JSON. It does not pickle executable code or flatten the
frame into a screenshot. Hidden children stay hidden; no parent-wide opacity
reset is applied on restoration.

```python
from algovis import SectionHandoff

# At the end of a completed section:
SectionHandoff.save(scene, "local-handoffs/part-one.json",
                    exclude=(chapter_marker,))

# At the beginning of the next independently rendered section:
previous_art = SectionHandoff.load(scene, "local-handoffs/part-one.json")
scene.add(previous_art)
scene.play(SectionHandoff.transition(
    previous_art, FadeIn(next_heading), run_time=0.6,
))
```

The restored art can be selected and moved as ordinary Manim paths and images.
Its original Python subclasses, updaters and arbitrary callback functions are
not restored. For continued mathematical manipulation, use the shared factory
to create the original component at the exact same geometry and adopt it in
place. The actual rendered cut must verify that this adoption changes no pixels.
Camera frame and background mismatches fail explicitly. Missing predecessor
artwork requires rendering that predecessor first.

## Ordered rebuilding

A review catalog can declare `"continues": "previous-section-id"` on a section.
Keep dependencies in catalog order. A change to a predecessor also invalidates
its successors. The reviewer renders them in dependency order, including when
another clip is selected. A successor waits outside the Manim lock until its
predecessor succeeds. Ordinary catalogs without continuations retain their
existing active-clip-first behavior.

The reviewer compares the new opening frame with its predecessor before
publishing. A mismatch preserves the previous working preview and saves the
two frames and comparison under the section's local continuity report.

## Actual frame checks

```powershell
python -m algovis.review.boundaries --catalog review_sections.json --output .qa/joins
```

This compares each actual last video frame to the next first frame and writes
six-frame boards showing the surrounding change. It uses the video stream's
duration, not an audio/container duration that may extend beyond its last frame.
The report includes the exact video hashes. Inspect the boards and the motion
around each changed opening, then run the word-level timing and layout audit.

An explicit `continuityIgnoreRegions` list may exclude a deliberately changing
chapter marker, using normalized `x`, `y`, `width`, and `height`. Record what an
exclusion means; it must not hide content changes. The numeric check tolerates
small compression differences by smoothing codec ringing at a one-pixel radius
in a 480p frame. Both raw and comparison metrics remain in the report. Native
serialization also has an exact painted-pixel regression test. The encoded
comparison certifies a visually matching cut, not the clarity,
timing or appropriateness of the subsequent transition. Verify assembly after
encoding too, and hold the last video frame through any remaining audio tail.
