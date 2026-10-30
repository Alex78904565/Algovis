# Reusable lesson objects

Scene code supplies mathematical content, instructional intent and spoken cues.
Components own geometry, alignment, object ownership and reusable motion. Extend
the component when the same meaning and behavior recur. Use a new component
when the new construction has substantially different meaning or behavior.

## Structure

```text
LessonAnimation               the narration timeline
└── SceneSequence              all planned states of one explanation/proof
    ├── scene states          final layouts, with a shared fitting contract
    └── component actions     intrinsic motion on verified spoken cues

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

For an algorithm correctness proof, call
`proof.define_algorithm(recurrence, base)` with the actual native mathematical
objects already constructed. This retains their identities and rejects a
prose correctness claim in the definition slot, including later refinements.
The English intended meaning belongs in the claim. Plain mathematical proofs
can still add their definitions directly.

`MathRow.part('future*')` selects existing named terms sharing a prefix as one
read-only attention span. The terms retain their individual identities for
substitution, semantic paint and native TeX layout. This lets a whole recursive
call receive attention while its increasing index remains separately editable.

`IllustratedBag.with_state(attempt=source)` carries a temporary item toward
the bag without corrupting its valid stored load. `reject_attempt=True` marks
it, and `return_attempt=True` sends it back. These operations are distinct from
storing a chosen item and updating the capacity meter. Content placement and
prop proportions belong to the illustrated components.

Use `IllustratedProblemScene` when a concrete illustration accompanies a taller
problem-data block. It centers the illustration vertically rather than treating
it as the first row of a two-column derivation. `ObjectRow(align_part='image',
align_edge='bottom')` puts differently sized props on the same visual ground.

A planned part can also be a complete semantic component, such as a base-case
`CaseEquation` inside a proof's definition stack. Its planned artwork is captured
at reference creation, separately from the live child resolved during playback.
Extracting it into the answer scene therefore retains both its identity and the
newly authored zero base, even before that proof timeline has played. Only a
mathematical term reference exposes `tex`; a component reference is not coerced
into a TeX string.

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

Content planning has its own clock too. Explicit `refine`, `revise`, `substitute`
and `reword` edits remember a detached model on the shared object. Passing it
to another layout, or copying it before playback, uses that latest authored
content. It never changes its live geometry or previously saved scene states.
After playback, subsequent authoring inherits the actual live result, including
intrinsic component actions. Use an earlier view's fork to revisit an explicitly
earlier state, rather than rebuilding it from an unplayed live placeholder.

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

Completed term transfers are consumed during native equation adoption. Reusing
the arrived equation later carries its content, not an instruction to copy
again from a source that may have left the board.

Choose `BlockScene` for a compact argument: its rows share a left edge while
the block is centered on both axes. `ComparisonScene` now uses centered blocks
by default; `center_blocks=False` is a deliberate top-anchor override. It uses
centered column blocks with a common vertical envelope. Their `SceneSequence`
reserves the completed widths and heights before incremental reveals.
Use `WorkedExampleScene` when problem data sits beside a calculation rather
than corresponding comparison rows: each panel reserves its own height and
is centered independently. A centered joint envelope alone can leave a short
equation panel visibly too high beside taller illustrations.
`ListScene` shares this centered block policy; `ProofSlide` retains its proof rail.

`SlotScene.add(..., fill='width')` gives an illustration its text peers' width
without letting the illustration determine that preferred width. The component
must implement `fill_width(width)`; plain text cannot be stretched this way.
`ServerRacks` scales its rack geometry and repositions its unchanged-size label.
Sequence planning measures future peer widths before the first filled item is
revealed. A future region allocation never reveals its future content.

`PairedScene(pairs=...)` reserves shared row heights for a method and its
corresponding examples. `ObjectRow` keeps the same children in a horizontal
container; its optional `align_part` aligns illustrations rather than their
different caption/meter bounds. `BracedGroup` owns a shared brace and heading
for related definitions. `SelectionScene` retains the items, illustrated bag
and arithmetic in their named regions. `IllustratedBag` owns a `CapacityMeter`
and its stored pictures; declaring `store=SlideObject(item.image)` in a planned
refinement visibly carries a copy while keeping the source item on screen.
Semantic components expose named `parts`, `motions_to(..., skip=...)` and
`adopt_layout` so transferred parts are not also faded in or copied twice.

Layout containers preserve **declared child identities**. To add a brace,
caption or other child, construct another container from the existing children
plus the new ones. Do not add anonymous children inside a layout-only
`refine`: a child-count mismatch fails instead of silently dropping them.
For example, construct `ItemCollection(*cards, count=Equation(...))` when
introducing the count, retaining the same cards. Semantic components such as
`CaseEquation` own their explicit protocols for adding/removing internal parts.
Components can declare `_algovis_content_fields` for non-geometric state that
must participate in reconciliation after intrinsic processes.

Reconciliation runs at every composition beat, not only the first beat after a
component action. It follows retained child identities through replacement
layout containers. The compiler compares successive authored models to find
explicit content/semantic edits, then carries the completed live state into the
new layout. Comparing against an already hydrated target mistakes inherited
state for a new edit and can reset it on a later caption-only beat. Test a reveal
and semantic change through regrouping and at least two later composition beats.

Normalize inherited children with their owning placement's fit. A child can
carry a local scale marker of 1 while its enclosing layout has scaled all its
geometry. Trusting that local marker compounds the fit on each later edit.
Exercise a fitted multi-card collection through several different card updates;
unchanged frames and metric insets must remain stable throughout the timeline.

Small primary dependency diagrams can choose a scene type role through
`RecursiveTree(label_type_role='equation')`. Dense trees keep the default
supporting label role. This changes the component's layout contract rather
than adding local font sizes or offsets. Plot descriptions likewise use the
scene's text/math statement roles; tick numerals remain supporting labels.

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

Scene typography assigns role defaults to incoming text and equations before
fitting. A supplied absolute font size does not override that policy. Reusable
components receive the same typography contract and own their internal reflow.
Check the active lesson builders as well as the library: implementing this
policy is not evidence that every existing clip has been migrated.
The [source audit](TYPOGRAPHY_AUTHORING_AUDIT.md) follows local authoring imports
and rejects manual sizing and placement in lesson builders.

### Plan an explanation's complete layout before its first step

Scaling belongs to the sequence containing the related scenes. A proof's early
state must account for its later fractions, additional lines and substitutions.
Use a named group and add every state before playback:

```python
movie = LessonAnimation()
proof_steps = movie.group('Induction proof')
proof = ProofSlide('Induction')
hypothesis = proof.add('induction_hypothesis', Equation({
    'call': 'f(k)', 'eq': '=', 'value': r'\frac{k(k+1)}2'}))
proof.add('inductive_step', Equation({
    'call': 'f(k+1)', 'eq': '=', 'child': 'f(k)', 'rest': '+(k+1)'}))
proof_steps.add(proof, on='next_case', reason='Start the larger instance')
applied = proof.fork().substitute(
    'inductive_step', child=r'\frac{k(k+1)}2',
    from_definition=hypothesis.part('value'))
proof_steps.add(applied, on='use_hypothesis',
                reason='Carry the hypothesis into its application')
movie.play(self)
```

The group measures all detached states, chooses one fitting scale per type/layout
channel, and reserves each proof row's maximum height and mathematical ascent
and descent. Earlier states have that same layout even when later content has
not yet appeared. Planning never inserts future objects into a visible scene.
Unreadable content fails before the group starts; it cannot silently acquire a
new scale partway through. A played group is sealed. A different explanation
can start a new group; a longer proof needs to be replanned as a complete group.
Nested groups inherit their enclosing group's fitting contract.

A proof's conclusion shares its body fit even when it occupies the footer.
Graph components reflow their coordinate geometry to keep labels at the scene's
label size. A comparison layout routes a copied definition through its gutter
when the direct path intersects another retained object. These are shared
layout policies rather than per-scene offsets.

The timeline stores `snapshot()` plans, preserving the definition applications
attached to that exact transition. An ordinary authoring `fork()` begins the next
state and clears those one-time applications. Fitting and playback must not turn
a requested definition transfer into an ordinary text morph.

Intrinsic processes also need a future envelope. A `RouteTrace` reserves its
complete route and cost line while revealing one city at a time; a tree can
reserve hidden leaf counts with `view.refine('tree', leaf_counts=True)`.
Components with structurally different attachments transition their named children
separately, avoiding Manim's container-padding copies. Illustrated objects share
unchanged image buffers between plans and detach them before opacity or color
changes, so planning many states does not duplicate the same bitmap repeatedly.

Use `view.copy('row')` to copy a planned state that has not played yet, and
`view.part('row', 'term')` to borrow a term introduced by an earlier planned
state. The mathematical content is known while authoring; its actual source
artwork is resolved when the copy plays. The source must then be visible.
Intrinsic cell filling and tree revealing also survive the next scene: the
timeline carries their live results into unchanged component models while
preserving explicit content and semantic edits in the destination.

Review manifests record the sequence name and common fit. A passing layout
contract still needs encoded-frame, copy-route, cue and audio inspection.

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
`auto_fit=False` to disable fitting while retaining scene typography, or pass
`auto_fit=FitPolicy(min_scale=.85, min_font_size=20)` for stricter limits.
`layout_report()` records the actual scale as well as alignment overrides.
Prepared diagram canvases retain their explicit component geometry; a raw Manim
`Scene.add` is not an automatic-layout operation.

Declare a relative type hierarchy with `font_scale`, rather than choosing local
point sizes:

```python
board.add('note', 'A smaller supporting explanation.', font_scale=.85,
          font_reason='Supporting context below the main result')
board.add('important', MathRow({'value':'f(1,0)'}), column='right', font_scale=1.2,
          font_reason='The requested answer is the focus of this composition')
refined = board.fork().set_font_scale('note', .9,
                                    reason='Keep supporting context subordinate')
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

`ListScene` derives from `BlockScene`: its rows share a left edge while the
completed argument is centered horizontally and vertically. Use `SceneSequence`
for a growing explanation so its final dimensions are reserved from the first
step. `PairedScene` reserves both columns and paired row heights, centers the
whole argument and exposes the resulting regions for validation. Wrapping uses
the full column capacity rather than an earlier short row's current width.

`ProofSlide` aligns a `work` row with no `call` part at the preceding
`inductive_step` row's `eq` part. This supports a continuing equality without
inventing a repeated left-hand side or manual indentation.

Proof and column copies share a measured route beside intervening rows. Named
parts retain their source owner, so consecutive source terms placed consecutively
at the destination travel together as one readable formula. Independently routing
those terms down the same gutter can make the copies collide with each other.
The bundle is only a travel container; destination term identities remain intact.

`StateCell.connection_point(direction)` intersects a ray from the frame center
with the frame. Trees use that contract for initial, reflowed and folded
connectors. A shape's support point is not generally that ray intersection.

`InductionChain.propagate(indices, trigger=..., reason=...)` owns the complete
correctness process, including a visible pulse for every listed case. Multiple
cases form one ordered process under their plural spoken phrase. Its initial
`known` cases can be supplied when their truth has already been established.
The same labeled boxes become readable dominoes whose labels remain inside and
rotate with the physical frames. Their contact geometry remains explicit.

`StateSequence.with_state(continuation=True, final_index='n')` adds an ellipsis
and a terminal symbolic state while retaining the concrete computed cells.
The enclosing sequence reserves the complete generalized row before revealing
that extension.

Transitions own the route as well as the destination. `ColumnSlide` routes a
borrowed definition around intervening body rows using the measured source and
destination bounds. It fails when no in-bounds gutter fits the copy. This is a
layout default, not a narration-specific offset. Inspect the encoded route when
changing its source formula or surrounding rows.

A definition application is a one-transition instruction. Snapshots retain its
identity so adding another row to the same authored view cannot replay it.
Explicitly applying the definition again creates a new instruction. Component
copies follow the same rule: adopted transfers are consumed, not stored as
permanent content behavior.

If a new plain label occupies a retained object's movement corridor, the view
compiler moves the retained work first and reveals the label in the cleared
space. Both phases belong to the same word-anchored transition; there is no
second attention cue. Deferred construction prevents the label from prepainting.
This safeguard does not certify arbitrary component motion or copy paths.

Retained objects adopt the destination's typography metadata on arrival,
before a later source-cleanup phase. Geometry and the font reference must agree
throughout that phase; stale peer metadata cannot certify a new layout.
During resizing between different layout contexts, a moving row has a temporary
peer group for its own terms. Its source remains in the outgoing proof group.
The measured size is retained throughout travel; the destination's settled peer
contract applies on arrival. Comparing a departing, resizing row against its
stationary source would incorrectly treat those two layouts as one composition.

`SelectionScene` fits the bag's readout and item-card metrics as peers. Component
geometry can reserve space, but treating one label-bearing component as an
independently shrinking diagram would give equivalent labels different sizes.

`DiagramScene` (including `DefinitionScene` and `TreeScene`) centers its
explanation block while retaining a shared left edge for its rows.
`TreeExplanationScene` uses the same contract for its equations. `block_slots`
declares this placement separately from `centered_slots`, which centers each
independent diagram. A `SceneSequence` measures completed block widths after
common fitting, then reserves those widths in every state without adding future
artwork. Inspect both early and completed states; do not replace this with local
position offsets. Explicit proof rails and full content columns retain their
own layout contracts.

`ConversionScene` has `left`, `right` and `connector` locations. Supply a
heading/call `MathStack` on each side; the connector aligns between the calls.
Adding cost rows below preserves that alignment. Use ordinary `ComparisonScene`
for independent arguments rather than putting a directional arrow in one column.

`MapScene` reserves `meaning` above a centered `map`, plus the shared footer for
route traces. Instance data can grow without moving the map or its hidden
prices, traveler and dashboard. Outline reveals preserve transparent fills so
the current city stays readable.

Before adding drawing code, inventory earlier and later occurrences. Reuse an
existing component, supply a style/layout strategy, or subclass it for a genuine
specialization. Add a separate component for a different semantic purpose.
Keep narration-specific examples out of reusable classes. Exercise meaningful
extension points with tests and real rendered examples; then rebuild and inspect
every affected lesson context. A helper existing in the library does not prove
that the production actually uses it.

Component refinements declare non-geometric state in `_algovis_content_fields`.
For example, `Checklist.visible`/`recursion_brace` and
`PseudocodePanel.visible_lines` distinguish a spoken reveal from inherited
paint. `SlideView.refine` rejects drawing changes with no declared content or
semantic change. Components with named child references implement
`motions_to`/`adopt_layout` to preserve those references; a generic Manim
`Transform` is not a substitute for adopting their state.

Proof substitutions prepare the surrounding terms before the copied formula
arrives. The shared proof sequence reserves a landing band for its working
equality, and the measured route avoids a retained suffix on the last leg.
Endpoint clearance alone does not establish a safe substitution path.
