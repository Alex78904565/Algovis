# Agent self-review before viewer review

Use this workflow alongside [the animation quality standard](ANIMATION_QA_STANDARD.md)
and [the recurring feedback reference](RECURRING_REVIEW_FEEDBACK.md).
The agent owns this work across the whole lesson. The viewer's selected section,
approval status, and willingness to watch another preview do not limit it.

## Observe the images, then compare

Every visual verification record must include image-derived observations and
an explicit comparison, using the [review template](templates/VISUAL_OBSERVATION_REVIEW.md).
Do not substitute a contact-sheet count, a source-code description, or a passing
geometry report for either step. This is a human/agent review procedure; writing
the report does not mechanically certify that the images are good.

1. **Capture the actual revision.** Generate contact sheets from the encoded
   video: settled compositions, before/during/after each change, internal helper
   boundaries, and affected section joins. Record video hash, frame numbers,
   frame rate and times. Inspect native frames or crops when a sheet is too
   small to read. Do not certify a frame you cannot read.
2. **Describe what is visible first.** Before consulting the animation notes
   or implementation for this comparison, write observations from the images.
   Identify actual text/math, visible groups, relative placement, alignment,
   spacing, type hierarchy, colors, and what remains or changes between samples.
   Describe each panel separately as well as the whole composition. Say where
   an equation sits relative to its panel and neighboring artwork, not merely
   that it is "centered." Distinguish visible facts from uncertainty. Do not
   infer an animation from its class name, cue label, or intended purpose. Prior
   familiarity is not an independent blind review; do not present it as one.
3. **Compare observations with the requirements.** For each applicable criterion,
   link the specific standard, observation IDs/frame evidence, animation note,
   surrounding timestamped narration, and relevant implementation. The standards
   and current explicit author instructions supply the acceptance criteria;
   notes describe intent and code explains causes. Matching the code cannot
   excuse a visible standards violation. If intent conflicts with an applicable
   standard, repair the plan/code; resolve material ambiguity with the author.
   Flag stale or conflicting notes explicitly. Do not rewrite a requirement
   merely to make the current render pass; identify the author instruction or
   narration revision that supersedes it, or leave the discrepancy open.
   Record `pass`, `fail`, `unverified`, or `not applicable`, with a reason.
   Read the board from a novice student's perspective, top to bottom. Write
   its actual chain: definition/prerequisites → claim → assumptions → reasoning
   → conclusion, using the roles applicable to that slide. Identify any missing
   justification, incompatible retained claim, premature notation or misplaced
   statement. Naming every visible object does not establish that this chain
   makes sense. A contradiction blocks visual acceptance even when geometry,
   timing and object retention checks pass.
4. **Repair, render, observe again.** A failure or missing required evidence
   prevents signoff for that criterion. Preserve the original failed observation
   and working parts, repair the shared cause where appropriate, then repeat the
   image description and comparison on the new encoded revision. A changed
   implementation alone does not close the finding. Link both records in the
   handoff and state the actual scope; do not promote local success to a
   whole-lesson approval.

The comparison must cover layout/grouping and typography; semantic color;
mathematics and visual prerequisites; retained work and section continuity;
spoken references and attention; and motion/lifecycle where applicable. Require
specific observations rather than blanket adjectives such as "clean" or
"professional." An unchanged feature can inherit only specific still-valid
evidence, never an invalidated signoff. Keep viewer endorsement separate.

Static images cannot establish exact word synchronization, smooth motion, or
sound quality. Compare the actual rendered intervals with timestamped words,
inspect denser frames/playback for motion, and review audio separately. Mark
those checks unverified when their evidence is missing; do not silently call
them inapplicable or pass them from a still image.

Example: "The short equation panel shares the tall item panel's top edge; its
lower margin is much larger than its upper margin" exposes a placement problem.
"The combined content fits and is centered" does not test the required
independent centering of those two panels. The observation must be precise
enough to discover the failure before consulting the layout implementation.

## Required evidence

Repair the owning abstraction before changing individual occurrences. Identify
whether a failure belongs to sequence planning, view transitions, a component's
internal lifecycle, or the lesson's mathematical/narrative content. Mechanical
failures need shared fixes and regression coverage, then an inventory of all
callers and inspection of their rebuilt output. A section-specific delay,
offset, scale, or cleanup is not an acceptable substitute for that repair.
Lesson-specific changes remain appropriate for the actual mathematics, wording,
and spoken cues; record that distinction in the finding.

For reopened feedback, invalidate the affected visual signoff. Write a small
acceptance record for each note: required visible behavior, old failure,
underlying cause, every affected use, inspected phase range, and observed
result. Mark it incomplete until that observation is actually made. A sample
count, passing bounds, exact cue time or retained ID is not a substitute.
Inspect all frames of short/problematic motions, including a plural process's
later successors, rather than accepting a clean middle or final frame alone.
Preserve mathematically meaningful presentation choices even when another form
is technically equivalent. If the existing renderer cannot support the
requested motion clearly, use the author's accepted simpler transition instead
of certifying an incoherent morph.

Run the [source sizing inventory](TYPOGRAPHY_AUTHORING_AUDIT.md) across the active
scene entry points and shared components. Identify ordinary text that still uses
absolute/manual sizing, separate legitimate diagram geometry, and inspect coverage
outside opt-in typography groups. A migrated animation timeline does not establish
that the scene owns its text sizing. Keep remaining migration findings open.

Before checking timing differences, review each active cue as a semantic pair:
**spoken referent/action → visible target/change**. Read the surrounding words,
not only the cue name. Record why the first matched word introduces that target.
Literal values should not appear on earlier filler words. A compound expression
may need separate cues for its factors and its final result. Then check the
specific word occurrence and the actual encoded start. These are two independent
checks; clock accuracy cannot establish semantic correctness.

For each changed cue, inspect encoded frames before, during and after its start.
Include the gap between consecutive repeated-word reveals. Preserve valid action
cues and definition-copy routes that already follow the explanation. Do not
replace them indiscriminately with the last noun or the final result's timestamp.

Generate a ledger from the **rendered timeline**, the narration cues, and the
timestamped spoken words:

```powershell
python -m algovis.review.audit --catalog review_sections.json --output .qa/animation-self-audit/current
```

The output includes one Markdown document and one JSON record per section:

- Actual start, end, duration, animation kind, target, and source location
- The explicitly intended spoken trigger, matched words, and timing difference
- The words spoken during the effect, with individual start and end times
- Objects retained, removed, and added by every play
- Text removed and subsequently recreated under another object identity
- Input hashes, so an audit of an older render cannot pass as current evidence
- A definition transfer's `copyContract`, when available: initial formula
  equivalence, structured destination, source/destination glyph counts and the
  chosen copy strategy. A later snapshot can show a different object type after
  the same row has been edited. Missing older metadata requires inspecting the
  actual construction before declaring that use unaffected.

`--section SECTION_ID` restricts an incremental check. An incremental repair must
still be checked against the surrounding lesson and the previous all-section audit.

The rendered manifest records composition snapshots before and after a play.
Old manifests without that evidence are marked incomplete. Original formula labels
are captured before transforms mutate them; the report should describe the change,
not merely its final appearance.

## Decide the animation before rendering

Before editing a crowded or repeatedly criticized composition, sketch two or
three arrangements using its final text, not placeholder lengths. Record the
chosen arrangement and why the alternatives were rejected. Prefer an established
proof, recurrence, comparison, or diagram format when it fits. Fix the content
column, row order, type hierarchy, and reserved future space before timing reveals.
Use `ColumnLayout` and `LessonStyle` to enforce those choices without shrinking
individual rows. An overflow means revising the plan, not reducing one peer's size.

For each conceptual change, write down:

1. **Why:** what new fact or relationship does this make easier to understand?
2. **Words:** which spoken word introduces it? Record the actual phrase.
3. **Target:** which existing object or mathematical term is being discussed?
4. **Action and duration:** reveal, move, substitute, box, pulse, or leave still.
5. **Continuity:** which useful content stays? What must move to make room?
6. **Need:** would removing this caption, marker, or transition make the argument
   harder to follow? If not, remove it before rendering.
7. **Quantity:** does this keep the established meaning, name, units, and type of
   bound? If it introduces another quantity, where is their relationship explained?
8. **Prerequisites and retained steps:** which values must already exist, and
   which exact intermediate expressions must remain alongside the result?

A preceding `wait_for_cue` provides context. It does not justify every later
animation until the next cue. A pulse after a reveal, color change, or another
play may already be late. Its actual interval must be compared with the words.

Declare attention deliberately:

```python
self.wait_for_cue("fifth_value")
self.play(Pulse(fifth_cell, trigger="the fifth", reason="Name the stored value"),
          run_time=0.6)
```

`spoken_focus` also accepts `trigger` and `reason`, including for a boxed term.
Never infer permission to pulse solely from a cue name. Remove an effect if
there is no specific spoken referent or it adds nothing beyond an existing reveal.

For new content, prefer one atomic word-timed operation:

```python
self.play_on_cue("total", FadeIn(total), run_time=0.5,
                 reason="Reveal the total when its value is spoken")
```

Set `transcriptWords` in the cue document to the timestamped words file, relative
to the project root. This method resolves the phrase against those words; the
cue's numeric time only selects the occurrence. A missing/approximate alignment
or a missed word fails the render. It does not silently play late or shorten an
earlier animation. Its timing declaration cannot leak to the next `play`.

The reviewer checks attention and explicitly word-timed content **before**
publishing the new video. A rejected attempt leaves the last good preview
available. A correctly timed pulse does not validate an earlier reveal: check
when the underlying value first becomes visible, not just its emphasis.

Verify the choice of trigger as well as its timestamp. Write the thought that
introduces the change and check its onset against the recording. A matching word
halfway through that thought can still be the wrong trigger. Include preceding
cleanup in the measured first-visible time. Legacy plays without word-timing
evidence are unverified, not zero-error timing passes.

Definition transfers carry a rigid copy of the glyphs, then visibly substitute
parameters or values after arrival. Do not carry a background patch or fade the
copy away before the result exists. Adopt the final result with identical geometry
on the same frame. Route the copy clear of other work when possible. Inspect the
travelling copy, arrival, local substitution, and cleanup as well as the final row.

An intentional destination type-size change happens continuously during travel,
finishing at arrival. Distinguish that from an accidental mismatch between peer
rows: compare source and destination term sizes and spacing before animating.
Include operators in the typography contract, and derive peer expressions from
the same equation component. Matching letters and a valid destination baseline
do not establish consistent formatting between the two expressions.

## Work through the findings yourself

- **Algorithm proof:** compare the retained native recursive/base equations
  with the English correctness claim. They have different roles. Check the
  exact predicate, base-instance name, induction assumption and quantified
  conclusion, including the change from a one-item base to a no-items base.
  The first/second recursive calls must follow the order of the recording.
- **Worked selection:** calculate the stored load after every action. A failed
  attempt must return its picture and restore the valid arithmetic before an
  optimality claim. Check that only the new item's numbers travel and that the
  card frames do not resize as attributes appear.
- **Readability:** inspect whether reserved space serves visible ink or motion.
  A proof fitting without overlap can still have excessive gaps and tiny text.
  A tree spanning several steps must not be forced into one recipe row.

- **Missing trigger:** remove the effect or supply its specific, justified words.
- **Before/after word:** correct the cue or the scheduling. Include time spent in
  nested groups, transitions, and previous plays.
- **Approximate word alignment:** recover the spoken words from the recording;
  do not divide a whole mathematical expression into guessed equal intervals.
- **Large clear:** check whether this is a real change of topic. Retain and move
  the existing argument if the narration still depends on it.
- **Recreated content:** inspect the frames. A deliberate return to an earlier
  example is different from erasing a line and recreating it two seconds later.
- **Dense construction:** count new ideas, not individual glyphs or drawing
  primitives. Reusing a brace and two rows can be clearer than a single new panel.
- **Missing derivation:** name the exact example, general rule, substituted
  expression, and result that must coexist. Keeping other proof rows does not
  excuse deleting the requested intermediate step. Check mathematical dependence
  separately from a warning about the number of animation primitives.
- **Premature guide or value:** verify prerequisites in the actual nested
  sequence. Future animation targets must remain absent until their turn; an
  addition guide needs both base inputs visible before it appears.
- **Retained identity:** compare adjacent compositions for continuity of meaning.
  A retained object fraction cannot certify that the explanation still flows.
- **Referenced target:** inspect the text inside the focused object, not just its
  border. A timing pass cannot establish opacity, layering, or readable glyphs.
- **Graph placement and styling:** check the visible plot's balance in the full
  frame, its labels, and the rationale for every marker and color change. Keeping
  a curve clear of a caption does not establish a good layout.

Record a specific disposition and frame evidence for each remaining finding.
Do not mark the user's preflight checks as approved on their behalf. A generated
report, zero overlaps, or passing tests do not constitute editorial signoff.

## Render and verify

Inspect the start, middle, and end of every changed transition. Check the complete
composition, including diagrams, guides, arrows, labels, and chapter marker.
Inspect continuous motion separately where three frames cannot establish it.

For grouped explanations, compare their actual left edges across the complete
composition. Check function meaning, recurrence, and base case together, then
every proof row and its continuations. Repeat after adding parameters and after
moving content into the proof rail. Prefer stable left anchors to separately
centered rows. Check that fixed input data and changing state have explicit
labels and consistent color roles in both examples and symbolic expressions.
Check rendered font sizes as well as glyph bounds: a fraction has a taller box
than a short formula at the same type size. Declare peer equation groups where
possible so the timing ledger can catch accidental later scaling. Notes, diagram
labels, headings, and primary equations may differ by an explicit hierarchy;
two peer claims must not differ just because one was harder to fit.

Apply these contracts to existing scenes as well as new layouts. Use
`LessonStyle.watch` to register peer equations without resizing them, and
`align_rows` for a shared left anchor. When a call moves into a deliberately
larger answer role, put it in that role's group and build replacements with
`math_like`; do not insert smaller arguments into an enlarged function.
Recheck both the construction and proof/reference layouts. A correctly sized
base case must not shrink again when it joins the proof rail.

Compare typeset parts after a local substitution, rather than treating the
whole expression's height as its font size. A taller fraction is not a bigger
font. Copy transfers and there-and-back focus effects must preserve the
destination's inspection metadata. Check the rigid copy's actual hierarchy,
including when a selected term lands in a differently grouped formula.
Registering metadata does not certify unregistered content, semantic color
meaning, or the visual quality of a complete composition.

For an overview of a completed build, sample the relevant animation's end, not
the end of the cue's inherited pause: the latter can put the sample into the
next transition. Use the actual animation records and neighboring frames to
distinguish a settled composition from a travelling copy or a layout change.

For multi-phase helpers, inspect each internal boundary and neighboring video
frames, not only the outer play's start, middle, and end. In particular check
definition travel, arrival, substitution, and adoption with repeated symbols and
different group structures. The right start and final result do not rule out a
brief glyph swap. Compare rendered text heights, diagram orientation, and the
scope implied by note placement across adjacent compositions.

Check the ledger against the recording: named references must receive appropriate
attention on their words; claims must not anticipate the narration. Inspect dense
proofs and all meaningful composition clears across every section.

Check audio separately. Speech recognition and peak measurements do not establish
that a transition sounds natural. Preserve raw takes and sample counts; protect
speech when removing noise from pauses. State any listening limitation or pickup
needed instead of claiming a perceptual audio check that was not performed.

Only after repairs and verification should a note move to `pending_review`, with
a concrete explanation and a `reviewAt` cue for the first visible effect of the
repair. Do not reuse the screenshot timestamp when the change begins earlier.
Preserve the original evidence and verify that clicking the ready note starts
at the repair, with the appropriate transcript cue selected. Only the viewer
resolves it. Answer annotation questions
in their threads, and leave unresolved repairs visibly pending. Assemble the full
preview after the section checks; repeat checks only for subsequent changes.

New feedback on an audited behavior invalidates that behavior's earlier signoff.
Record the new finding and its required evidence; do not reuse the previous
zero-error summary as proof. Updating prevention documentation is not an animation
repair and must not move the corresponding repair out of the pending queue.
Preserve the earlier record as history and attach the new note IDs, failed
acceptance criterion, and required new evidence. Record successes just as
specifically: viewer praise for a domino fall does not approve an unrelated
substitution, and resolving earlier notes is not approval of the whole section.

An agent finding a visible failure must invalidate its own signoff as well.
For partially revealed components, inspect the immediate regrouping and the
following caption-only beats: a preplanned snapshot must not restore hidden
children later. For a labeled shape morph, inspect every encoded frame of the
short phase for text occlusion and label ownership, not just arrival bounds.

For local math changes, inspect a native baseline as well as font size. Use the
named-term `MathRow` contract for arguments and numeric branch calculations.
Check the intermediate arithmetic and both alternatives side by side; one
correct total does not certify the other. The publication gate rejects recorded
native-layout drift and explicitly declared incorrect additive equalities.

For sustained spoken references, declare the start and release cues with
`focus_on_cue`. Check the whole lifetime, including a settled frame during the
explanation and the release at the next referent. The manifest gate rejects a
box that disappears early or remains after release. Neither this gate nor the
math contract certifies an undeclared object or a complete composition. Inspect
the actual video for clutter, meaningful grouping, proof retention, and motion.

Review controls are part of the authoring workflow: verify playback speed while
playing and seeking, persistence across section changes and reloads, and music
tracking the same media clock. Use pitch preservation when the browser supports
it. Check the toolbar at the ordinary reviewer width, not just a wide desktop.
