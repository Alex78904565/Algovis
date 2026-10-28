# Shared lesson components

For artwork that continues across independently rendered sections, use the same
factory on both sides and verify the actual cut. `SectionHandoff` also carries
native artwork into a deliberate topic transition without changing narration
time. See [section continuity](SECTION_CONTINUITY.md).

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
| Editable mathematical row | `MathRow` | One native TeX baseline, named terms, consistent substitutions and optional numeric sum check |

Proof profiles (`worked`, `detailed`, `compact`, `diagram`) reserve different
vertical space for algebra or an adjacent diagram. They use the same shared
label and content columns. Equation profiles (`stacked`, `split`, `inline`)
express the orientation chosen before construction; they are not separate
visual styles for different algorithms.

Align proof labels with the first line of their content, rather than the
center of a multiline block. `ProofFrame.label_target(row, first_line)` plans a
label copy while leaving live artwork untouched; reveal or move the real label
on the corresponding content cue. Preserve the content's existing geometry.

## Resolve competing color meanings

Follow the [semantic precedence](../VISUAL_LANGUAGE.md): good/bad evaluation
outranks known/completed status, then operation, structure and neutral context.
Use `theme.role_color('retained', 'bad')` for a correctly derived poor runtime,
or `style.math(..., role='bad')` for an explicitly unfavorable statement.
`good` overrides lower roles with the success color; `bad` overrides them with
the danger color. The order of arguments does not choose the winner.
Conflicting explicit good/bad evaluations raise an error and need a clear
comparison context. `AlgorithmComparison` and `RecurrenceComparison` apply this
rule to their slow/improved runtime labels; their headings remain neutral.

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

For changing arguments or arithmetic, typeset the complete next row instead of
centering individual replacement glyphs on the old glyph boxes:

```python
call = MathRow({"f": "f(", "item": "i", "comma": ",", "weight": "w", "close": ")"})
next_call = call.next_layout(item="1")
self.play_on_cue("first_item", *call.motions_to(next_call), run_time=.7,
                 reason="Substitute the first item into the call")
call.commit(next_call, self)
```

Names remain stable through the substitution. `part("weight")` selects that
term. Uniform movement and scaling preserve the row's layout contract; moving
one argument off its baseline creates an error in the real render manifest.
`ApplyDefinition` preserves this structured destination. For explicitly additive
numerical examples, call `require_sum()` with named immediate/future/total terms.
This checks completed equalities while allowing symbolic and incomplete stages.

For a simple replacement, let the scene handle planning and adoption together:

```python
self.substitute_on_cue("first_item", call, item="1", run_time=.7,
                       reason="Substitute the first item into the call")
```

`MathRow.tokens("f", "(", "i,w", ")")` supports migration of existing
tokenized equations, retaining `MathTex`'s 48-point default. Its terms have
string names `"0"`, `"1"`, etc. The last
two children are invisible baseline anchors; use explicit term indices or
`part("3")`, rather than `[-1]` or an unrestricted slice. Native static
`MathTex` equations need no conversion. Migrate editable arguments, delimiters,
and numerical arithmetic; do not break a working diagram merely to change its
class. After adding parameters, use the row's motions and commit rather than
assigning a new `submobjects` list, which discards its baseline contract.

Use `focus_on_cue("take_reference", take_call, until="skip_reference", reason=...)`
for an extended spoken reference. Separate targets receive separate boxes. The
next named `play_on_cue` releases them; its absence is a publication error.
`extra=(FadeIn(range_label),)` can reveal the associated explanation in the
same slot; `buff` preserves the established outline spacing. A brief spoken
name can still use `Pulse`. A selected branch's permanent success outline is
semantic state, not automatically a transient attention box.
Use `play_on_cue(..., edge="end")` when an action must wait for the whole phrase
to finish, such as returning an item after explaining why it does not fit.

### Require timing coverage, including older animations

Set `require_word_timing = True` on a narrated scene after migrating it. A raw
content `play` then fails at render time, and undeclared changes in its manifest
fail the publication audit. A successful shared-helper test alone does not
establish that every older scene uses that helper.

- `play_opening(..., reason=...)` establishes the initial composition at time
  zero. It cannot be used later in the section.
- `play_on_cue` starts one change on verified words.
- `transition_on_cue` clears and reveals one composition on verified words,
  preserving the existing transition's internal phases.
- `play_phase("same_cue", ..., reason=...)` completes a dependent mechanical
  phase of the most recent declared process. Its real offset is recorded. It
  cannot name an unrelated or superseded cue.
- `with self.cue_sequence("collapse", reason=...):` starts a multi-step process
  such as folding repeated subtrees. Its phases share one verified start;
  they are not falsely reported as separate animations all starting on that word.

Use a new spoken cue for a new caption, explanation, or attention effect. A
phase is appropriate for carrying and settling the same copied value, or the
next fold of an already introduced collapse. It must not become the old
pattern of letting arbitrary later actions inherit a broad cue. Attention
effects retain their independently checked exact spoken referents.

Prepare new targets offscreen. If a helper needs to directly recolor or unhide
an **already visible** object before construction, call `wait_for_word(cue)`
before that preparation, then use `play_on_cue` as usual. Python evaluates the
arguments before entering `play_on_cue`; its wait cannot undo an earlier
`set_color`, `set_opacity`, or `add`. Otherwise a color can appear early even
though the pulse itself is correctly timed. Prefer `.animate` inside the cued
operation when possible. A preparation wait does not authorize a raw `play`.

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

All 17 narrated DP sections now require declared word timing. Editable call
arguments, delimiter changes and numerical recovery rows use `MathRow`; extended
references use held focus with a named release. Complete static equations and
brief, explicitly spoken-name pulses retain their existing components. The
migration preserves the established proof rails, equation frames, state rows,
story illustrations and native section handoffs. Rebuild and inspect every
dependent section after changing these shared components; an installed helper
is not evidence that an older scene actually uses it.

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
