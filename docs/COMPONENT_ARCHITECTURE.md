# Reusable lesson objects

Scene code supplies mathematical content, instructional intent and spoken cues.
Components own geometry, alignment, object ownership and reusable motion. Extend
the component when the same meaning and behavior recur. Use a new component
when the new construction has substantially different meaning or behavior.

## Structure

```text
Manim VGroup
├── StateCell                  one framed state/value
│   └── CallNode               a recursive call; grows around its label
├── StateRow                   contains StateCell instances
├── RecursiveTree              contains CallNode instances and edges
├── ProofRow                   owns a label and its content
└── Proof                      contains named ProofRows
    └── InductiveProof         a prepared correctness-proof summary

SlideScene
└── AlgorithmLessonScene       derive/prove/compare teaching workflows

ViewScene                     preferred scene with view timelines/word attention
└── ViewSceneMixin             also composes with AlgorithmLessonScene

SlideView                     detached composition at one point in the lesson
├── ColumnSlide               a shared left-aligned column
├── SplitSlide                two columns inside the body region
├── EquationSlide             named rows from EquationFrame
└── ProofSlide                named rows/labels from ProofFrame
    CanvasSlide               positioned components with their own layout rules

SlideObject                   stable live artwork; copy() records a new identity
ViewTransition                difference between compositions, played by SlideScene
```

These visual classes compose `SemanticProperties` and shared style/layout
objects. They do not need a deep inheritance tree merely to obtain a theme.
`ProofFrame`, `EquationFrame` and `ColumnLayout` are layout strategies;
`PanelFrame`, `CaseEquation` and `ChapterMarker` serve distinct visual meanings.
A comparison panel, a state cell and a bag's capacity meter are not interchangeable
just because each happens to contain a rectangle.

## Plan compositions, then transition

A Manim `SlideScene` owns the section's clock. Each visual beat can be a small
layout instance; it does not need another Manim Scene subclass. Constructing or
forking a view only arranges detached targets. It cannot move the live objects
while the narration is still explaining an earlier composition.

```python
first = ColumnSlide('Using a definition', theme=self.theme)
definition = first.add('definition', MathRow({
    'call': 'f(k)', 'equals': '=', 'value': r'\frac{k(k+1)}2'}))
self.transition_to(first, cue='definition', run_time=.7,
                   reason='Introduce the definition')

next_view = SplitSlide(first.object('title'), theme=self.theme)
next_view.add('definition', definition)          # retain the same object
next_view.add('application', definition.copy(), column='right')
self.transition_to(next_view, cue='apply', run_time=1.5,
                   reason='Carry a copy to its application')
```

`SlideObject.copy()` creates a new object at the original's position and records
its source. At the cue the transition takes the source's current geometry,
carries a visible copy to the target, and keeps the original if it is retained
in the next view. Ordinary Manim `mobject.copy()` remains an unrelated copy;
explicit provenance avoids accidentally turning every cloned style or target
into an instructional transfer.

Copies inherit their source formatting by default. A destination may intentionally
use another shared type role or declared relative scale, such as moving a large
working equation into a smaller reference area. Interpolate that formatting
continuously during travel; do not finish the move and then reformat at rest.
Peer equation rows in the same composition share their type size and mathematical
spacing. Build a worked instance from the same named-row component, with a copy
or `next_layout`, rather than reconstructing it from separately scaled fragments.
Register operators with the same typography contract as their neighboring terms;
an unregistered multiplication sign can evade an otherwise passing peer check.

`ApplyDefinition` also supports equivalent TeX landing in an editable `MathRow`.
Its travelling copy matches visible glyphs rather than incompatible term/group
wrappers and invisible baseline anchors. The destination keeps its named parts
and native layout, so later substitutions remain editable. Name the parameter
separately from its units; replacing a count should not replace `states` as well.
Already edited glyphs can contain extra curve subdivisions; those are aligned
within each corresponding glyph. An equivalent structured copy with unmatched
glyphs fails explicitly instead of silently using container-level matching.
Only painted leaf paths count as glyphs. Earlier edits can leave invisible SVG
paths or degenerate padding on containers; those must not become letters during
a later copy. Inspect a path's own geometry and paint, rather than its children's
combined bounding box.
Rendered transfer records include a `copyContract` with the initial equivalence,
structured-destination flag, glyph counts and chosen strategy. Inspect that
initial contract rather than the destination's type after later substitutions.

The transition rules are:

- The same object in both views stays present and moves only if needed.
- A provenance copy travels from its visible source rather than fading in.
- Other new objects enter after unrelated outgoing content has cleared.
- Objects omitted from the next view retire. A source needed for a copy stays
  until that copy arrives.
- Unchanged artwork receives no gratuitous pulse, fade or color change.

Use `view.fork()` for a small refinement of the same board:

```python
applied = proof.fork().substitute(
    'inductive_step', child=r'\frac{k(k+1)}2',
    from_definition=hypothesis.part('value'))
self.transition_to(applied, cue='hypothesis', run_time=1.2,
                   reason='Use the induction hypothesis in the child call')
```

Equations use native `MathRow` terms. Substitution preserves their identities,
type size and baseline; a definition-use relationship copies only its selected
term. Column rows reserve their mathematical ascent/descent, so simplifying a
fraction does not pull the unchanged function or following rows upward. Proof
labels follow the first line using the existing `ProofFrame` convention.

`view.target(name)` exposes detached final artwork for inspection or styling;
`view.preview()` produces independent final artwork for a still. `set_view(view)`
installs an opening/cut composition without animation and keeps independent
objects such as a chapter marker. The renderer saves its own outgoing snapshot,
so later edits to the author's view cannot rewrite what it thinks is visible.
`ViewTransition.describe()` exposes retained, moved, copied, substituted, new
and removed items before rendering. Play planned transitions through `SlideScene`
so deferred ownership changes are redrawn rather than cached as static text.

Layout validation rejects overflow, overlap between separate logical items and
duplicate ownership. Groups are layout containers: their children keep their
identities when separated, moved to another group, or recombined. Retiring a
layout container does not erase a child retained in the next view. A semantic
component remains intact until one of its children is explicitly extracted.
Optional `via=` waypoints or `path_arc=` route copies around intervening work;
clear final layouts alone do not certify clear motion paths.

The existing procedural `Slide` and animation-based `transition(...)` APIs remain
supported. This is an authoring layer, not an automatic conversion of previously
written lesson scenes. Migrate an existing composition deliberately and preserve
its working layout, narration cues and section handoff. Do not mix legacy slide
lifecycle operations and view transitions without explicitly adopting the board
with `set_view`.

See [the rendered-example source](../examples/layout_transitions.py). It has
three short animations and a still-layout example, with no private lesson assets.
Final-position checks are necessary; inspect intermediate motion, word timing
and ownership as well. Deferred view transitions redraw current objects each
frame to avoid stale background copies of earlier equations.

## Good alignment is the default

Use `ColumnSlide` for related explanations, `SplitSlide` for parallel panels,
and `EquationSlide`/`ProofSlide` for their named rows. Adding content aligns it
to the shared anchors, reserves enough space and preserves peer type sizes.
Overflow fails instead of silently shrinking an individual row.

An intentional departure uses `view.offset(name, vector, reason='...')`.
`LayoutOverrideWarning` makes that exception visible. `view.layout_report()`
also detects unexplained direct target shifts and identifies boards with several
overrides. Reconsider the layout before adding another offset. Unchanged,
previously reported offsets do not emit another warning on every inspection.

`CanvasSlide` serves positioned components such as a recursion tree, a route map
or an established shared proof frame. Its `include` operation explicitly retains
that component geometry. It rejects ordinary `add`: use an automatic layout
for a new stack of text or equations. A canvas is not an excuse to hand-position
repeated explanatory rows or to bypass the ink-level layout audit.

## Fit content by default

Implementation status: fitting and relative-size support are available, but
prepared raw Manim objects still retain their supplied natural font sizes.
View compilation alone does not establish scene-owned typography. Use the
[source sizing audit](TYPOGRAPHY_AUTHORING_AUDIT.md) to identify remaining manual
construction before claiming a production migration is complete.

`SlideView`, `ColumnSlide`, `SplitSlide`, `EquationSlide` and `ProofSlide` fit
their detached targets before arranging them. Plain strings use the shared body
type and wrap to their content column. Related content shares a fitting scale,
including both columns of a split layout; a wide formula does not silently get
a smaller font than its peers. Equation baselines and first-line proof-label
alignment remain component constraints. Replanning starts from natural sizes,
so adding several rows cannot repeatedly shrink earlier content.

```python
board = SplitSlide('The choices')
board.add('meaning', 'The best additional value from the items under consideration.')
board.add('recurrence', MathRow({'call':'f(i,w)', 'rhs':'=...'}), column='right')
```

The default `FitPolicy` permits scaling down to 72% and requires text to stay at
least 16 points. Content that still cannot fit fails with a readable-capacity
error: split the explanation or select a more suitable layout. Use
`auto_fit=False` to keep exact authored sizes, or pass
`auto_fit=FitPolicy(min_scale=.85, min_font_size=20)` for stricter limits.
`layout_report()` records the actual scale as well as alignment overrides.
Prepared diagram canvases retain their explicit component geometry; a raw Manim
`Scene.add` is not an automatic-layout operation.

Declare a relative type hierarchy with `font_scale`, rather than choosing local
point sizes:

```python
board.add('note', 'A smaller supporting explanation.', font_scale=.85)
board.add('important', MathRow({'value':'f(1,0)'}), column='right', font_scale=1.2)
refined = board.fork().set_font_scale('note', .9)
```

The final size is the natural role size times `font_scale` times the shared fit
scale. Fitting therefore preserves the declared size ratios. A retained object
inherits its ratio in the next view unless a new one is supplied. The reviewer
checks the underlying peer sizes after accounting for these explicit ratios,
and the report lists the overrides. Readability limits still apply. Set label
sizes through a diagram's own styling rather than scaling the entire diagram
with `font_scale`.

See `examples/automatic_layout.py` for wrapping, shared scaling and retained
objects returning to their natural size when more space becomes available.

## Multi-phase views and component animation

Use `ViewScene` for new scenes, or mix `ViewSceneMixin` into an existing lesson
scene. A cue-driven timeline can retain component-specific drawing and motion:

```python
self.view_on_cue('next_calls', tree.get_depth_reveal_anim(2),
                 run_time=.7, reason='Expand exactly the next layer')
self.view_on_cue('apply', Then(
    CopyInto(definition, application, run_time=.8),
    Later(lambda: Replace(application, simplified), run_time=.5)),
    run_time=1.3, reason='Carry the definition, then simplify its application')
```

`Reveal`, `Retire`, `Move`, `CopyInto`, `Replace`, `Draw` and `WriteView` describe
the corresponding view operations. `Together`, `Then`, `Stagger` and `Later`
describe their timing. Each active phase constructs a detached `CanvasSlide`
and a `ViewTransition`; native Manim interpolation is its motion policy.
Already-working component animation factories are lowered into the same view
timeline, including their nested reveals, copies and cleanup. There is no
second procedural scene path for helper-added effects.

Moving a container that includes `MathRow` uses the row's named-term motions
and native-layout adoption. Baseline anchors never turn into painted symbols
when the text changes. Keep destinations as `MathRow` too, using `next_layout`
for a substitution. Changing a container's children calls for explicit
reveal/retire operations, rather than silently aligning unrelated child counts.
Term motion tracks its intended point size throughout interpolation and adopts
the destination's font calibration at the endpoint. A different letter's ink
height must not change its reported point size or create a false mismatch
between equation terms; actual size changes still interpolate normally.

Gated phases activate at their actual start, including overlapping staggers.
Preparing a later phase cannot introduce future objects. Layout containers
change ownership without changing their children's geometry or identity.
Completed component artwork uses `mount_view`/`unmount_view` for explicit
adoption/retirement. Retirement follows the whole object family even after a
layout container has dissolved into independent roots; retiring a handoff must
not leave its old boxes under the new factory's artwork. The review manifest records every view phase, its cue,
duration, object difference, copy sources and completion under
`viewInfrastructure`. Canonical animation kinds remain available to the existing
reviewer and word-timing audit.

Resolve a spoken cue once. The verified-word scheduler checks alignment before
playing; another tiny wait can round up to an extra video frame and push the
following process past its next word. Do not compensate by weakening the timing
gate or moving the audio.

## Declare attention on the object

```python
call = board.add('recurrence', MathRow({
    'call': 'f(', 'argument': 'n', 'close': ')=f(n-1)+n'}))
call.part('argument').on_word('input_size', style='box', duration=.5,
                             reason='Identify the input inside the function')
```

The cue names a verified transcript phrase. `ViewScene` schedules the declaration
while waiting or during another view animation; it does not need a separate
pulse beside every narration call. `bind_attention(target, cue, ...)` provides
the same declaration for existing component objects. An optional
`callback(scene, target)` supplies a specialized effect.

Bind the intended occurrence of a word, using its named narration cue. A common
word such as "value" appearing later does not automatically pulse every object
that once mentioned it. Declare another cue binding for an intentional repeated
reference. The duration belongs to the attention declaration; the containing
transition's duration does not silently stretch the effect.

`auto` boxes a selected equation term and pulses an isolated object. Explicit
styles include `pulse`, `box`, `fill` for a framed object, and `plus` for an
existing operation token. A binding never invents an unexplained plus sign.
Effects preserve semantic paint, including during a simultaneous status change.
A copy does not inherit its source's automatic bindings. An already-clear reveal
can supply the attention itself.

Missing/late word alignment, invisible target glyphs and an effect extending
beyond its declared time slot fail explicitly. Attention keeps its own absolute
word clock even when a caption retires first. Permanent mathematical changes
belong in the view program; use attention callbacks to direct attention.

## Properties determine color

```python
style = LessonStyle(theme=my_theme)
bound = style.math(r'O(2^n)', status='computed', evaluation='bad')
```

The object retains its properties. The theme resolves them through the
[precedence rules](../VISUAL_LANGUAGE.md): evaluation, known/completed status,
operation, structure, then neutral context. A computed poor result remains red.
Use `SemanticChange(bound, evaluation='good')` on a new spoken evaluation; its
construction cannot recolor the live object while waiting for that word.

`set_semantics` also binds ordinary Manim objects. A cell applies meaning to its
frame while retaining neutral value ink. Native `MathRow` substitutions carry
these declarations to their adopted terms. The review manifest exposes them.
Explicit legacy `color=` arguments remain supported; they are not evidence that
an old object declares all its meaning. Prefer properties in new and migrated
code, and record the actual migration scope.

## Cells and call nodes

Both square call nodes and array entries use `StateCell` and `StateCellStyle`.
`CallNode` adds label-fitting and call-specific shape choices; the tree owns
branching, positioning and edges. `StateRow(cell_type=...)` and
`RecursiveTree(node_type=..., node_style=...)` are explicit extension points.
An existing `node_factory` remains available for genuinely different artwork.

```python
cells = StateRow(['', '', ''], theme=my_theme)
self.play_on_cue('first_value', cells[0].populate(1),
                 run_time=.4, reason='Fill the first base value')
```

Population enters the value and its computed status together. Preparing that
animation leaves the live cell blank. Population inherits the parent component's
scale; a value that does not fit requires a wider cell, not a silently
shrunk label.

## Proofs own row alignment

```python
proof = Proof('detailed', theme=my_theme)
self.play_on_cue('proof_start', FadeIn(proof),
                 run_time=.6, reason='Establish the proof structure')
self.proof_row_on_cue('claim', proof, 'claim', claim_text,
                      run_time=.6, reason='State what we will prove')
```

Rows use named parent-relative anchors. Their labels track their first line,
including after copying or moving a component. Supply `first_line=` for a
special mathematical arrangement whose first line is not its first explicit
row. The progressive helper waits for the cue before adding live content and
consolidates ownership afterward. Complete proofs can use `proof.add_row` before
they are revealed. `ProofFrame.bind`/`align` provide the same row constraint for
retained artwork in an existing scene, without moving its mathematical content.

## Apply existing work

```python
self.apply_definition_on_cue('substitute', definition_rhs, child_call, result,
                             run_time=.8, reason='Apply the induction hypothesis')
```

This is the shared `ApplyDefinition` operation: preserve the source, carry a
readable copy, replace only the application and adopt one result. For replacing
a complete proof row, pass `proof=proof, row='base_case'`; alignment and ownership
are adopted too. Partial editable equations use `MathRow` planning and commit,
or `substitute_on_cue`, so a digit is never merely centered on an old letter.

## Extending the system

Before adding drawing code, inventory earlier and later occurrences. Reuse an
existing component, supply a style/layout strategy, or subclass it for a genuine
specialization. Add a separate component for a different semantic purpose.
Keep narration-specific examples out of reusable classes. Exercise meaningful
extension points with tests and real rendered examples; then rebuild and inspect
every affected lesson context. A helper existing in the library does not prove
that the production actually uses it.
