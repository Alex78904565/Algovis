# Animation, slide, panel and object ownership

This is an audit and a proposed authoring contract. The current library does
**not** yet have the full recursive-panel model described below. The shared
layout repairs in `52263ba` are implemented; this document does not claim that
they constitute that further migration.

## The ownership chain

```text
Animation                     spoken cues, complete plan, global identities
└── Slide                     one explanation and its planned steps
    └── Panel                 arranges its own children
        ├── Panel             panels can nest recursively
        │   └── Object        equation, tree, text, illustration, state row...
        └── Object
```

These are ownership relationships. Specializations supply layout recipes:
columns, rows, an independently centered comparison, a proof, or a diagram
beside an explanation. A proof panel can contain a label column and a working
column; the working column can contain nested equation panels. A panel need
not have a visible border.

The slide arranges its top-level panels. Every panel arranges its own children.
Objects own their intrinsic drawing and named parts. The animation coordinates
changes between these planned states, including moves between different panels.

## What the current code actually does

| Responsibility | Current implementation | Remaining gap |
| --- | --- | --- |
| Schedule steps on spoken cues | `LessonAnimation`, `SceneBeat`, `ActionBeat` | No missing clock layer; preserve the strict word checks |
| Plan an explanation before playback | `SceneSequence.compile`, `plan_sequence` | Measurements use specialized flat-view hooks instead of a recursive panel contract |
| Describe a slide at one step | `SlideView` and its detached snapshots | Public names mix the meanings of slide, scene and sequence |
| Arrange related content | `SlotScene`, `ColumnLayout`, proof/equation frames and specialized `_arrange` methods | Named regions act like panels but are not first-class panel objects |
| Own visual objects | `SlideObject`, `Placement`, component named parts | Placements currently live in `SlideView.items`, a flat dictionary |
| Keep an object across steps | `fork`, `retain_live_models`, `ViewTransition` | Ownership must extend across arbitrary nested panel paths |
| Carry a copy | `SlideObject.copy`, definition-use declarations, `ApplyDefinition.bind` | Preserve this provenance through panel flattening |
| Change content in place | `revise`, `refine`, `substitute`, component motions | Replacement at the same named panel slot is not a universal rule for unrelated new handles |
| Nest groups without losing children | Layout components and retained child records | Generic recursive panels still need a common measurement/placement interface |

`PanelFrame` is a drawn frame. It is not currently the missing recursive layout
owner. Adding more border classes would not establish this ownership chain.

## Plan all steps, then measure them

The author's flattening idea is appropriate for **measurement**. It must not
insert future objects into the live Manim scene with opacity zero. That approach
has previously allowed future labels and edges to leak into earlier frames.

1. Record every intended panel/slide step before playback. Each step identifies
   its visible objects and named positions; detached future content is available
   for measurement.
2. Measure object variants at natural, role-based typography. Include wrapping,
   cases, labels, and the object's intrinsic diagram geometry.
3. Measure nested panels from their children upward. Reserve the largest needed
   geometry for each stable position and the largest complete panel state. A
   temporarily hidden future row can reserve space without being drawn.
4. Allocate panel space from the slide downward. Resolve wrapping and a common
   typography fit for the complete explanation. Relative type-size declarations
   express deliberate hierarchy; per-object absolute scaling remains exceptional.
5. Reserve copy departure, corridor and landing space as part of the plan.
   Endpoint fit alone cannot make a moving expression clear neighboring text.
6. Compile the visible states and transitions. Fail before publication when the
   complete explanation cannot fit readably.

Measure mutually exclusive alternatives as alternatives. Physically overlaying
all versions or summing the height of objects that never coexist would create
misleading reservations. Keep fit scope at one coherent explanation, such as
one proof, rather than shrinking the entire hour to its single largest slide.

This extends the existing sequence-wide sizing mechanism. It should replace
special-case layout ownership, not add a second independent renderer.

## What `next()` means

During authoring, `next(on=cue)` records another planned state. It does not run
an animation immediately or mutate live geometry. During playback, advancing
uses the already compiled state, so the panel's text size cannot change merely
because another row has become visible.

A panel step changes that panel's content. A slide step can change its panel
arrangement. Changes on the same cue form one coordinated transition. The
animation resolves timing and cross-panel movement for the complete visible
tree, rather than allowing each panel to independently fade its old contents.

The existing snapshot/fork implementation is suitable machinery for this. A
`next()` interface can be simple without making the underlying plan mutable at
playback time.

### Passing the next placement down the tree

The proposed propagation protocol is:

1. The slide provides each panel's planned bounds and the panel it replaces or
   follows, if any.
2. Each panel recursively provides its children with their next bounds, named
   positions and typography constraints.
3. One shared identity pass supplies an object transition context: its current
   and next placements, retain/copy/replace relationship, source, destination
   content, semantic paint and required dependencies.
4. `panel.next(context)` asks its children for their next transitions. Nested
   panels do the same. An object's default transition handles ordinary movement
   and formatting; specialized objects can supply named-term or tree motions.
5. The slide/animation runner schedules the returned transitions together on the
   verified spoken cue, including necessary copy-before-retirement phases.

No child starts its own Manim playback while the parent is still planning.
Unchanged objects return stillness. Advancing a step does not imply a pulse or
other attention effect; those still require a specific spoken purpose.

The shared identity context matters when an object leaves one panel and enters
another. The outgoing panel releases ownership and the incoming panel accepts
it, but its motion is compiled exactly once. Panels must not independently
interpret that transfer as a fade-out plus an unrelated reveal. Objects receive
enough context to construct their motion without choosing their own layout or
inferring identity from coordinates.

## Resolve identity before arranging motion

Positions are stable **named slots**, such as `proof.inductive_step.expression`,
not comparisons of floating-point x/y coordinates. Layout may move a slot.

Match the whole visible panel tree in this order:

| Relation between steps | Compiled behavior |
| --- | --- |
| Same object identity, including a different panel | Retain it and smoothly move/style it to its new placement |
| New object with `copied_from` provenance | Begin a copy at its source, preserve the source, and move/format the copy continuously into its destination |
| New object replaces the occupant of the same named slot | Use the relevant content-replacement transition in that slot |
| Unmatched new object | Reveal it at its declared cue |
| Unmatched outgoing object | Retire it after any dependent copies finish |

Global identity matching must precede slot replacement: otherwise moving an
object between panels would be mistaken for two unrelated removal/addition
operations. A visible object has one owner at a time. Showing the same content
in two places requires a copy. Moving a layout container preserves the logical
identities of its children; regrouping children does not replace them.

Slot replacement uses object capabilities. An equation can transform its named
terms; a tree can retain nodes/edges. Substantially different objects need an
appropriate replacement transition, rather than an arbitrary glyph morph.

## Implementation boundaries for a further migration

- Introduce a real recursive panel state with named children, measurements,
  layout policy and step history. Make existing scene convenience classes build
  these panels rather than retaining separate arrangement algorithms.
- Flatten the planned panel tree into the current view compiler's leaf
  placements, preserving object identities, source references, semantic paint,
  typography ownership and attention bindings. Panel paths locate content;
  they do not replace object IDs.
- Move sequence measurement to a recursive interface. Keep proof baselines,
  intrinsic component geometry, shared type roles and copy clearance as explicit
  constraints rather than opaque offsets.
- Define the new-object/same-slot replacement rule and reject ambiguous duplicate
  ownership. Keep the existing explicit replacement API usable during migration.
- Verify nested growth, cross-panel moves/copies, splitting/regrouping, changed
  wrapping and intermediate motion. Use the current checked videos as regression
  references. Do not announce full migration based on class names or endpoint
  tests alone.

The result should let a lesson author describe content, grouping and spoken
steps. Choosing coordinates or independently correcting sibling font sizes
should not be ordinary lesson code.
