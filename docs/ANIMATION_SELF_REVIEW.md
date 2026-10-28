# Agent self-review before viewer review

Use this workflow alongside [the animation quality standard](ANIMATION_QA_STANDARD.md)
and [the recurring feedback reference](RECURRING_REVIEW_FEEDBACK.md).
The agent owns this work across the whole lesson. The viewer's selected section,
approval status, and willingness to watch another preview do not limit it.

## Required evidence

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

## Work through the findings yourself

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
