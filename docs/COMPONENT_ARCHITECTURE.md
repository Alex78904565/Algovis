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

SlideView                     detached composition at one point in the lesson
├── ColumnSlide               a shared left-aligned column
├── SplitSlide                two columns inside the body region
├── EquationSlide             named rows from EquationFrame
└── ProofSlide                named rows/labels from ProofFrame

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

Layout validation rejects overflow, overlap between separate logical items,
duplicate ownership, and ambiguous parent/child reparenting. Group intentionally
overlapping artwork inside one component. To retain individual children across
views, bind those children separately in both views rather than retiring their
parent. Optional `via=` waypoints or `path_arc=` route copies around intervening
work; clear final layouts alone do not certify clear motion paths.

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
