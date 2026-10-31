# Animation, slide, panel and object ownership

This began as an audit of the missing recursive-panel layer. That layer is now
implemented in `algovis.panels` and `algovis.panel_slide`, and the existing public
slide layouts now supply panel recipes to the same recursive arranger. This
source migration is distinct from verification of the regenerated lesson movies;
the private release record tracks those renders and their visual comparison.

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
| Plan an explanation before playback | `SceneSequence.compile`, `plan_sequence` | Native frame policies retain their specialized reservations; `PanelSlide` also measures arbitrary nested future positions |
| Describe a slide at one step | `SlideView` and its detached snapshots | Public names mix the meanings of slide, scene and sequence |
| Arrange related content | `Panel`, `RowPanel`, `RegionPanel`, specialized proof/paired/analysis panels | Every exported slide uses `SlideView._arrange`; recipes declare ownership rather than running a second placement pass |
| Own visual objects | Named panel children, `SlideObject`, `Placement`, component named parts | `SlideView.items` remains the compiler's flat compatibility projection, not an independent renderer |
| Keep an object across steps | `fork`, `retain_live_models`, global `ViewTransition` matching | Cross-panel reparenting retains object identity |
| Carry a copy | `SlideObject.copy`, definition-use declarations, `ApplyDefinition.bind` | Provenance survives panel flattening; source retirement waits for its copies |
| Change content in place | `revise`, `refine`, `substitute`, component motions, `replace_at` | A new occupant of the same named position in a forked explanation replaces it; unrelated boards do not match by coincidental names |
| Nest groups without losing children | Recursive panel measurement and flattened global matching | Hidden future positions reserve only layout data, never invisible live artwork |

`PanelFrame` remains a drawn frame. `Panel` is the separate recursive layout owner.
Adding border classes does not establish layout ownership.

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
5. Plan copy departure and landing as part of the explanation. A transfer may
   cross neighboring ink while traveling; it must arrive clear and aligned.
   Inspect the route for legibility, without imposing an empty corridor on every
   move.
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

The implemented propagation protocol is:

1. The slide provides each panel's planned bounds and the panel it replaces or
   follows, if any.
2. Each panel recursively provides its children with their next bounds, named
   positions and typography constraints.
3. One shared identity pass supplies an object transition context: its current
   and next placements, retain/copy/replace relationship, source, destination
   content, semantic paint and required dependencies.
4. `panel.next(event, contexts)` asks its children for their next transitions. Nested
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

### Word events and unconsumed triggers

Playback advances on a resolved, timestamped word event. Phrase, context and
occurrence selection belong to compilation, before a panel can advance; children
must not independently poll a string and hope they select the right utterance.
An ordinary transcript word does not require an animation. Every **declared**
visual step does require a valid anchor and a consumed transition, and every
declared attention binding must fire or be fulfilled by its matching reveal.

The owned `renderer.lesson_animation()` factory now registers the complete plan.
Scene teardown and reviewer publication reject unconsumed steps and attention,
including an unplayed nested sequence. Existing exact-word and late-trigger
checks remain in force. Old manifests without declaration coverage cannot
retroactively prove that every authored step fired. Standalone unregistered
plans are useful in tests, but lesson code must use the owned factory.

A rerecording must invalidate alignment provenance, then realign and rebind its
selectors. A missing, ambiguous or unused trigger must fail while the previous
preview remains available. `NarrationCue` supports one-based `occurrence` and a
containing spoken `context`. Equidistant ambiguous matches fail. `WordEvent`
carries the resolved interval and transcript fingerprint through slide, panel
and object advancement.

Optional `alignmentProvenance` binds a cue file to exact recording/transcript
bytes, checked on load and again at completion. Lessons can require it with
`require_alignment_provenance=True`. `tools/seal_narration_alignment.py` records
these fingerprints after alignment review; sealing is not speech alignment or
an editorial certification. A changed file must be realigned/reviewed before
resealing. Publication still enforces the actual rendered word timing.

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

## Implementation boundaries

- `PanelSlide` owns recursive named panel recipes; its detached forks are the
  steps. Existing scene convenience classes build shared column, proof, paired,
  conversion and analysis panels. They inherit one arranger instead of running
  their own geometry pass after it.
- Flatten the planned panel tree into the existing view compiler's leaf
  placements, preserving object identities, source references, semantic paint,
  typography ownership and attention bindings. Panel paths locate content;
  they do not replace object IDs.
- Recursive measurement reserves future named positions and internal gaps for
  `PanelSlide`. Native proof/equation recipes preserve their specialized frame
  constraints within the same sequence compiler. Keep proof baselines,
  intrinsic component geometry, shared type roles and copy clearance as explicit
  constraints rather than opaque offsets.
- Identity and copy provenance take precedence over same-position replacement.
  Duplicate ownership fails. A replacement source needed by a copy remains until
  the copy arrives, then changes in place. The explicit edit APIs remain usable.
- Verify nested growth, cross-panel moves/copies, splitting/regrouping, changed
  wrapping and intermediate motion. Use the current checked videos as regression
  references. Do not announce full migration based on class names or endpoint
  tests alone.

The result should let a lesson author describe content, grouping and spoken
steps. Choosing coordinates or independently correcting sibling font sizes
should not be ordinary lesson code.

## Authoring example

```python
film = self.lesson_animation()
explanation = film.group('apply one definition')
columns = RowPanel(gap=1)
left = columns.panel('definition', Panel())
left.add('equation', Equation({'call': 'f(k)', 'eq': '=', 'value': 'k+1'}))
columns.panel('application', Panel())

first = PanelSlide().add_panel('working', columns)
explanation.add(first, on='definition', reason='Introduce the definition')
second = first.fork()
second.add_at('working/application/equation',
              first.copy('working/definition/equation'))
explanation.add(second, on='apply', duration=1.5,
                reason='Carry the definition to its application')
film.play(self)
```

`reparent(old_path, new_path)` moves a handle without changing identity.
`replace_at(path, new_object)` gives one named position a new occupant.
`add_panel_at` adds a nested container; `remove` removes an object position.
Use relative `font_scale`/`font_reason` for an intentional hierarchy. The complete
explanation chooses the common fit before playback. See the runnable public
`examples/nested_panels.py` example.

The project-source gate rejects ordinary manual placement/sizing, direct scene
drawing, local layout overrides, and unowned animation plans, including imported
authoring helpers. This is an authoring lint, not a security sandbox for arbitrary
Python. The internal component canvas uses a fixed panel through the same compiler;
lesson source cannot import it as a layout escape hatch.

Deliberate transfers use gentle arcs by default. Temporary overlap during travel
is allowed by the author's latest clarification; final positions remain clear and
aligned. Existing specialized teaching motions retain their intrinsic policies.

## Rendering and publishing the compiled result

`RenderJob` gives each native render its own media, Pango text, TeX, object
manifest and handoff directories. Sharing a writable TeX directory is unsafe:
Manim's intermediate cleanup can remove another renderer's in-flight DVI files.
The text SVG cache has the same concurrent-writer problem. Handoff inputs are
seeded from the published predecessor, then written inside the new job.

The reviewer disables partial-movie caching for these fresh builds. It requires
the job's new manifest, validates source authoring, typography, alignment, spoken
timing and trigger consumption, and checks the predecessor cut before publishing.
A published revision pairs an immutable movie with its own `.objects.json`.
Only a successful build switches the served revision and updates canonical
copies; a failed build leaves the previous good preview available. This prevents
new object metadata from being served over an older video.

The native `examples/panel_motion.py` example exercises a whole case equation on
an arc. The shared mathematical lowering passes the containing path to every
term, brace and condition. Individual term transforms cannot silently revert to
straight paths while their owner curves.
