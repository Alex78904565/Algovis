# Algovis Storyboard Language

The storyboard is the reviewable contract between narration and Manim. It
describes what the viewer should notice at each spoken cue without specifying
coordinates, colors, or low-level animation classes.

## Two-level structure

A storyboard contains a small number of high-level `animation` blocks. Each
block states one visual goal. Its `component` entries are the phrase-triggered
changes that accomplish that goal.

This makes two reviews possible without watching the render:

1. Read only the animation titles and goals. Does the visual argument flow?
2. Read the components. Does every motion answer something being said at that
   moment, or are we animating merely because the screen has been still?

## Core rule

Every visible change belongs to a named narration cue. If the narration does
not introduce, compare, transform, or dismiss an idea, the default action is
`hold`.

When a component applies a definition or an induction hypothesis, its motion
must visibly connect source and application: keep the definition on screen,
carry a copy to the replaced term, and leave surrounding symbols unchanged.
The Manim authoring helper is `ApplyDefinition(definition, application, result)`.
For a crowded proof, its optional `via=[point, ...]` routes the copied formula
around intervening rows while preserving its glyphs. Keep the source visible.

Use `DeferredAnimation(lambda: animation)` inside a sequence when a future
guide or transform must stay absent until earlier steps finish. The factory is
constructed and activated at its own turn, so it can use the current layout.
For example, reveal both base values before constructing their addition guide.
Use `None` for the application when filling a blank part of the equation.

The exported storyboard records this as one semantic action:

```text
apply hypothesis.rhs -> expanded_sum replace=child_call keep_source=true
```

The transcript timeline also shows one **Apply definition** duration bar for
the transfer, rather than separate bars for its internal copy and fade.

```text
storyboard 2
section fibonacci_bottom_up "Fibonacci — Bottom-Up DP"
audio "assets/audio/fibonacci.wav"

animation duplicates "Expose repeated calls":
  goal "Follow the spoken calls, then distinguish retained work from repeated work."
  component duplicate_f5 say "also requests f of 5":
    focus tree.f5_duplicate role=current style=pulse
  component already_computed say "we've already computed f of 5":
    focus tree.f5_kept role=retained style=tint
    caption tree.f5_kept "already computed"
  component recompute_again say "we're computing it again":
    focus tree.f5_duplicate role=repeated style=tint
    caption tree.f5_duplicate "requested again"

animation collapse "Collapse the recursion tree":
  goal "Mark retained states green, duplicates red, and merge duplicates bottom-up."
  component collapse_duplicates say "the duplicate branches disappear":
    together:
      focus tree.spine role=retained style=tint
      focus tree.duplicates role=repeated style=tint
    merge tree.duplicates -> tree.spine order=bottom_up
```

## Semantic roles

Use roles instead of literal colors. The active theme owns the final palette.

| Role | Meaning | Default visual use |
|---|---|---|
| `neutral` | Existing context or ordinary structure | White or muted |
| `current` | The exact object currently named | Blue |
| `operation` | Arithmetic, movement, choice, or transformation | Yellow |
| `retained` | Computed, accepted, proved, cached, or kept | Green |
| `repeated` | Duplicate, rejected, impossible, or discarded | Red |

A node cannot change semantic roles merely because a later animation needs a
convenient color. For example, the retained occurrence of `f(5)` stays green
and the repeated request stays red.

## Attention styles

Choose the least intrusive style that answers “where should I look?”

- `pulse`: one already-isolated object is named.
- `box`: one term inside a larger expression is named.
- `arrow`: a relationship or direction is explained.
- `tint`: an object enters a persistent semantic state.
- `none`: no additional attention animation is necessary.

Do not flash a whole diagram when the narration refers to one node. Do not add
an attention cue after the relevant words have already passed.

## Actions

- `show target role=neutral style=fade`
- `hide target style=fade`
- `focus target role=current style=pulse`
- `transform source -> destination`
- `fill cell value=13 role=retained`
- `move object -> destination`
- `merge duplicates -> survivor order=bottom_up`
- `retain target`
- `clear target1 target2`
- `caption target "short local explanation"`
- `hold`
- `note "review-only explanation"`

Actions in a cue run in order. Put genuinely simultaneous actions inside a
`together:` block. A transition should normally clear the outgoing idea before
revealing the incoming one; use `together` only when overlap carries meaning.

## Timing

The cue name must exist in the section's cue JSON. An optional numeric offset
is allowed when two actions correspond to different words inside one cue:

```text
animation calls "Follow the first two calls":
  goal "Move the viewer's attention only when the narration names a call."
  component root_children +0.40 say "f of 6":
    focus tree.f6 role=current style=pulse
  component root_children +1.62 say "f of 5":
    focus tree.f5 role=current style=pulse
```

Prefer a new word-level cue when the word alignment is known. Offsets are for
small subdivisions of an existing phrase, not guesses.

## Validation and export

`Storyboard.load(path).validate(cue_path, require_all_cues=True)` checks the
grammar, semantic roles, styles, cue names, cue order, and cue coverage.

`Storyboard.density_warnings(cue_path)` reports components with too many visual
changes, changes unsupported by a spoken phrase, and active beats crowded too
closely together. The generated `DENSITY_REPORT.md` collects that audit for the
whole lesson. A warning is a prompt for human judgment, not an automatic ban.

Create or edit `.story` files for your lesson, then load and validate them
with the `Storyboard` API. `board.to_source()` serializes the reviewed
structure. Source-to-storyboard export adapters can be project-specific;
they do not need to be part of the rendering code.

## Review workflow

1. Transcribe or draft the section as a `.story` file.
2. Read the cue sequence without rendering and settle the visual argument.
3. Validate cue names, order, role use, and transition structure.
4. Implement or update the Manim scene from that approved contract.
5. Render the section by itself and inspect the exact word-level timing.
6. Render the full lesson only after every section passes its individual review.

The storyboard is the conceptual source of truth. Manim code may contain more
layout detail, but it should not introduce a new visual claim, color meaning,
or attention event that is absent from the storyboard.
