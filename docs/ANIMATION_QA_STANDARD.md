# Animation quality standard

This document turns the recurring review feedback for the dynamic-programming
video into production rules. It is a release gate, not a collection of optional
style suggestions. Every section should pass these checks before it is assembled
into the full video.

The narration is the timing contract. The storyboard is the visual contract.
The Manim scene is an implementation of both.

Use [the agent self-review workflow](ANIMATION_SELF_REVIEW.md) to produce and
inspect the actual word-level timing and composition ledgers before viewer review.
The [recurring feedback reference](RECURRING_REVIEW_FEEDBACK.md) is the compact
editorial checklist. An inherited cue is context, not a justification for a pulse.

## 1. Narration controls the screen

- A visual change begins on the word or phrase that introduces it, never before.
- Prefer a word-level cue. A guessed numeric offset is only a temporary fallback.
- If a phrase names `f(6)` and then `f(5)`, focus them in that order.
- If a phrase says “two more calls” and later “and so on,” expand two calls first
  and the remaining tree only at “and so on.”
- A visual may remain visible after its trigger, but it may not anticipate a
  claim the viewer has not heard yet.
- Silence is usable pacing room. Do not fill it with unrelated motion.
- Check that the chosen phrase introduces the thought, rather than merely
  containing a matching word later in the sentence. Measure the actual reveal
  after any cleanup; a correctly timestamped cue alone is insufficient.

## 2. Prefer one stable composition per idea

- Treat independently rendered sections as one visual sequence. Inspect the
  last/first frames together and the surrounding motion. Retain shared artwork
  across the cut; make genuine topic changes deliberately within the narration
  clock. Check the encoded assembly too. See [section continuity](SECTION_CONTINUITY.md).
- Build an argument in place. Avoid turning consecutive clauses into separate
  slides.
- Keep earlier useful work visible when the next line depends on it.
- Do not make an object disappear and later recreate it unless the narration
  explicitly leaves and returns to that idea.
- A transition clears the outgoing composition before revealing the incoming
  one, unless their overlap itself explains a relationship.
- Every paused frame should make sense as a screenshot.
- Preserve the reasoning as well as the object identities. Retaining one formula
  while repeatedly replacing its context can still produce a rapid slideshow.
- Refine an existing English definition into its mathematical form rather than
  discarding it to introduce the same idea on another page.

## 3. Animation must direct attention, not compete for it

Use the least intrusive device that answers “where should I look?”

- **Pulse:** one already-isolated object is named.
- **Box or underline:** one term inside a larger expression is discussed.
- **Arrow:** a relationship, dependency, or direction is explained.
- **Persistent tint:** an object's semantic status actually changes.
- **No animation:** the screen already makes the reference unambiguous.

Do not flash a whole tree when the narration refers to its base cases. Do not
pulse a term after the corresponding words have passed. Do not animate merely
because the screen has been still.

Inspect the target's actual glyphs before, during, and after the effect. A label
hidden by a fill or removed child is a failure even when the border pulses on time.

## 4. Color is semantic

Follow [the visual language](../VISUAL_LANGUAGE.md). In particular:

- Blue means structure, state, or the current object.
- Yellow means the active operation, choice, or optimizer.
- Green means known, stored, selected, valid, or complete.
- Red means invalid, rejected, or repeated waste.
- White is neutral content; gray is supporting scaffolding.

A temporary mention does not change an object's meaning. Use an outline or
scale pulse instead of recoloring it. The same object must keep the same role
across layout changes.

## 5. Equations grow with the reasoning

- Keep the function definition visible while its choices, state, base case, and
  recursive term are discovered.
- Translate English into mathematics in the same visual location.
- Align equals signs and case rows. Keep subscripts, parameter order, and symbol
  colors consistent.
- Do not show unexplained notation early.
- Labels such as “base case” and “recursive step” sit next to the rows they name,
  preferably on the left when they describe an entire row.
- Screen text should add structure or visual evidence, not transcribe every
  spoken sentence.
- Apply a visible definition or induction hypothesis by carrying a copy from
  that definition to the term being replaced. Keep the source visible. Use
  `ApplyDefinition(definition, application, result)` for this transfer.
- Replace only that term. Keep the function name, equals sign, unaffected
  terms, scale, and semantic colors stable. Do not morph a whole equation
  when only its right-hand side changes.
- Use one stable name per quantity. Show the reasoning when moving from a call
  count to an operation or runtime bound; do not silently relabel them as aliases.
- Distinguish exact values, approximations, upper bounds, and lower bounds.
  Keep an asymptotic growth statement qualified rather than implying equality.
- Show how a numeric example generalizes; changing its label to `f(n)` is not
  that derivation. A finite operation count must be established independently
  of big O, whose hidden constant and threshold are unspecified.
- Retain an explicitly requested substituted expression beside its final result.
  Preserving other proof rows does not satisfy that requirement.

## 6. Layout is relational

- Plan the completed composition before its incremental reveals. For a layout
  repair, compare a few sketches and record the chosen arrangement. Use named
  rows and nested regions rather than a new coordinate for every object.
- Use one rendered type size for peer statements. A separate heading, supporting
  note, or diagram label may use an explicit hierarchy. Check actual font size
  after transformations; equal initial scales do not prevent later drift.
- Inspect visual density and hierarchy separately from overlap tests. A frame
  can have no collisions and still ask the viewer to read too many things.
- Give the current idea one primary visual group, with supporting material
  clearly subordinate. Leave breathing room between unrelated groups.
- Consolidate repeated definitions instead of showing the same meaning above
  and below an equation. Clear temporary explanatory notes when their example
  takes over; retain earlier proof steps that later reasoning actually uses.
- Position elements relative to a parent group, anchor, or safe region. Avoid
  unrelated global coordinates for content that conceptually belongs together.
- Maintain readable spacing around titles, section labels, equations, arrows,
  braces, and graph bounds.
- Recenter a composition when its contents materially shrink or grow.
- Reuse the established equation, proof, parameter-definition, and comparison
  layouts. Keep peer formulas at the same rendered type size. In a comparison,
  align corresponding headings and calls without shrinking one entire argument.
- An ellipsis stands for omitted elements; it is not a boxed node with its own
  children. Center continuation dots within the clear gap they explain.
- Keep example data and the problem definition visible while using them. A
  numerical route total requires visible edge costs; comparing two routes
  requires retaining both routes and their totals.
- Center arithmetic operators on their mathematical factors independently of
  explanatory labels and underbraces. Inspect the actual glyph alignment.
- Inspect the balance of the visible plotting area separately from the bounds
  of its labels. Do not shift an entire graph off center to center its steep part.
- Before approving a transition, inspect the first frame, midpoint, and final
  frame for collisions, duplicated objects, off-screen content, and lingering
  edges.
- A split composition includes its labels, braces, arrows, and attention
  effects inside each half. Check these against the divider as well as against
  text; text-only collision checks do not detect a label crossing a rule.
- Derive state counts from the possible inputs to the function. Array notation
  can explain storage, but drawing rows, columns, or higher dimensions is not
  required for the recurrence, proof, population order, or runtime argument.
  Prefer parameter ranges and a compact shared-state diagram when a grid
  would suggest that the array's geometry is part of the method.

## 7. Manim object lifecycle rules

These prevent the pop-ins, duplicated layers, and lingering lines that have
recurred during review.

- Never `FadeOut` or transform a mobject that is not currently in the scene.
  Manim can briefly add it in order to animate it, which looks like a pop-in.
- Do not animate a temporary `Group` whose children already exist independently
  when the animation may copy or replace the group. Animate the owned top-level
  objects directly.
- After transforming members out of a container, remove the exact transformed
  source objects as well as the container.
- Edges belong to the same lifecycle as their nodes. A collapsed or removed
  subtree leaves no orphaned edges.
- A semantic object has one visible owner at a time. Never leave both the old
  and new representation stacked in the scene.
- Future targets in nested animation groups must remain invisible until needed.
  Verify prerequisites: both base values exist before their addition guide.
- Inspect internal helper phase boundaries and adjacent frames for symbol swaps
  or duplicate ownership, including formulas with repeated glyphs and different
  group structures. Outer start/middle/end samples alone cannot certify them.
- Defer each future substitution and cancellation phase with `DeferredAnimation`
  when composing a sequence. Deferring only a reveal does not prevent a later
  fade or transform source from entering the scene during an earlier hold.
- Use `SlideScene.transition` when outgoing and incoming compositions occupy
  the same space. It clears the old material before revealing its replacement
  within the original cue's time slot. Crossfading two sentences is an overlap.
- Use `ReplaceContent` for a different whole caption or layout. Reserve symbol
  transforms and `ApplyDefinition` for mathematical changes where following
  the symbols actually helps explain the substitution.
- Cleanup filters absent direct fade targets in the library. For a sequence,
  keep later cleanup inside that sequence, after its corresponding reveal.
- Do not reset a parent's opacity when it contains deliberately hidden art or
  transparent outlines. That can revive old icons and fill empty gauges. Dim
  visible parts or multiply their existing opacity instead.

## 8. Pacing and density

- Aim for one conceptual visual change per spoken clause.
- Simultaneous actions are reserved for genuinely simultaneous ideas.
- Hold dense equations and proofs long enough to read.
- Avoid rapid title changes and decorative captions that vanish before they can
  help.
- Prefer a local note beside the object it explains over a detached caption at
  the top of the frame.
- Remove any animation whose absence does not reduce understanding.
- Remove a caption if the retained formula, diagram, and narration already make
  its point. State a caveat once; do not create a second slide to paraphrase it.
- Give each plotted series a consistent meaning and color. A steepening curve
  does not justify a new color or point marker without a narrated reason.

## 9. Audio and music

- Dialogue timing, animation timing, and transcript highlighting share the same
  section timeline.
- Check every edit boundary, including silence inside a clip, for thuds, clicks,
  fabric noise, level jumps, and abrupt room-tone changes.
- Normalize dialogue consistently and use de-essing only as much as needed.
- Music supports pacing but never determines when an explanation becomes true.
- Audition music with dialogue ducking, then verify the section once with music
  muted so timing problems cannot hide behind the score.

## 10. Required review sequence

1. **Cue audit:** every visible change has a phrase-level trigger.
2. **Storyboard audit:** read only the animation goals, then the components.
3. **Static preflight:** run the project audit and resolve its errors.
4. **Section render:** render affected sections separately so fixes can be
   checked without rebuilding the entire video.
5. **Frame audit:** inspect the first, middle, and final frame of each transition.
6. **Playback audit:** watch once with narration and music, then once muted.
7. **Annotation pass:** answer or fix every queued note.
8. **User review:** fixes move to `pending_review`; only the reviewer marks them
   `resolved`. Handle every open note across the project, including drafts
   and follow-up questions, regardless of the selected section or its approval
   status. Section approval is the user's judgment of the lesson in context;
   it never limits which notes the agent handles.
9. **Assembly:** compile the complete video only after every section clears its
   agent verification checks. Outstanding `pending_review` notes and the user's
   section approvals never prevent fixing or checking the rest of the project.

## Approval checklist

A section is ready only when all answers are yes:

- Does each event start on the phrase that motivates it?
- Is the viewer's attention directed to exactly the object being discussed?
- Is there one stable composition for each idea rather than a rapid slideshow?
- Does useful prior work remain visible?
- Are semantic colors consistent?
- Are equations and labels aligned, readable, and free of raw markup?
- Are transitions free of pop-ins, duplicates, lingering edges, and overlaps?
- Does every paused frame make visual sense?
- Are dialogue levels and edit boundaries clean?
- Are all fixes awaiting review or resolved, with no unhandled queued notes?
