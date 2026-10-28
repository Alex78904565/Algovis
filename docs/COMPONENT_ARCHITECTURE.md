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
```

These visual classes compose `SemanticProperties` and shared style/layout
objects. They do not need a deep inheritance tree merely to obtain a theme.
`ProofFrame`, `EquationFrame` and `ColumnLayout` are layout strategies;
`PanelFrame`, `CaseEquation` and `ChapterMarker` serve distinct visual meanings.
A comparison panel, a state cell and a bag's capacity meter are not interchangeable
just because each happens to contain a rectangle.

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
