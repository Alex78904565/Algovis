# Shared lesson components

Repeated visual formats are implemented in `algovis/frames.py`. Change
`LessonFrameStyle` there to update the defaults for every caller on its next
render. Scenes supply mathematical content and spoken cues, rather than drawing
another copy of a proof rail or inventing another column position.

| Repeated format | Component | Shared decisions |
| --- | --- | --- |
| Proof rail | `ProofFrame` | Label wording, label size/color, label column, content column, divider, named row anchors |
| Developing equations | `EquationFrame` | Common left edge, named meaning/recurrence/state slots, term gaps, continuation alignment, width guard |
| English or mathematical alternatives | `CaseEquation` | One neutral brace, lhs spacing, left-aligned case rows, standard or compact row spacing |
| Comparison panels | `PanelFrame` | Border thickness, corners, surface, semantic border role, inset heading |
| Runtime comparison | `ComparisonFrame` | Column offsets and divider |
| Chapter marker | `ChapterMarker` | Position, type sizes, gap and colors |
| Page heading and safe regions | `Slide`, `SlideLayout` | Heading placement and frame regions |
| State/value row | `StateCell`, `StateRow` | Fixed cell geometry and value placement |
| Peer typesetting and substitutions | `LessonStyle`, `math_like` | Role-based sizes/colors and inheritance of the current rendered type size |

Proof profiles (`worked`, `detailed`, `compact`, `diagram`) reserve different
vertical space for algebra or an adjacent diagram. They use the same shared
label and content columns. Equation profiles (`stacked`, `split`, `inline`)
express the orientation chosen before construction; they are not separate
visual styles for different algorithms.

## Write the content, then reveal it

```python
proof = ProofFrame("compact", theme=self.theme)
claim = proof.place("claim", style.math(r"P(k): f(k)\text{ is correct}"))
base = proof.place("base_case", existing_base.copy())

# Moving prior work is still an authored animation on a measured spoken cue.
self.play_on_cue("proof_intro",
    existing_recurrence.animate.move_to(proof.anchor("definitions"), aligned_edge=LEFT),
    FadeIn(proof.labels_by_name["CLAIM"]), FadeIn(claim),
    run_time=.6, reason="State the claim as the proof is introduced")
```

`place` preserves the supplied object's identity and size. Layout construction
does not add any label, equation, future target or parent group to the scene.
Case rows use the actual supplied lhs and alternatives, so translating one
English row does not replace the other rows. Keep existing ownership cleanup
when the scene adopts a refined expression.

An oversized equation raises an error. Revise the composition or use the
appropriate profile; do not shrink one peer formula until it fits. Continue
using `LessonStyle.watch` and `align_rows` for the existing type/alignment gates.

## Existing production migration

The private DP production uses `ProofFrame` in the induction refresher,
knapsack, road trip and city-route proofs, including later changes of induction
index and base case. The public `InductiveProof` summary uses it too.

Knapsack, road trip, city-route and value-indexed constructions use
`EquationFrame`; their alternatives and the two backtracking decisions use
`CaseEquation`. The public Bellman helper uses the same alternatives component.
The general blueprint uses the shared equals-sign continuation layout.

Runtime split frames, recursive/array comparisons, state-reframing cards,
evaluation-method panels and conclusion miniatures use the corresponding shared
components. Standard panel styling also reaches the pseudocode helper.
Headings already use `Slide`; every narrated clip uses `ChapterMarker`.
Concrete story props, maps, plots and attention outlines retain their specialized
components: a graph axis or a bag is not a comparison-panel background.

## Rebuild every dependent section

With the review server's source watcher enabled:

- A library/helper edit queues every section in the catalog.
- A scene-source edit queues every section declared to use that file.
- A watched cue, transcript or audio file queues its own sections.
- The displayed section is requested first. Waiting requests coalesce; an edit
  during an active render requests another pass for that section.
- All requests share one Manim execution lock, including manual renders. A
  failed render keeps the previous published preview available.

For a source file containing the whole video, one source edit therefore queues
all its clips. Automatic rendering makes an updated preview available; it does
not mark visual checks approved. A shared layout change still needs rendered
frame inspection in each affected context before the agent hands it back.
