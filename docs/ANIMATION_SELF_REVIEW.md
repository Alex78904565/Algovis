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

For each conceptual change, write down:

1. **Why:** what new fact or relationship does this make easier to understand?
2. **Words:** which spoken word introduces it? Record the actual phrase.
3. **Target:** which existing object or mathematical term is being discussed?
4. **Action and duration:** reveal, move, substitute, box, pulse, or leave still.
5. **Continuity:** which useful content stays? What must move to make room?

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

Record a specific disposition and frame evidence for each remaining finding.
Do not mark the user's preflight checks as approved on their behalf. A generated
report, zero overlaps, or passing tests do not constitute editorial signoff.

## Render and verify

Inspect the start, middle, and end of every changed transition. Check the complete
composition, including diagrams, guides, arrows, labels, and chapter marker.
Inspect continuous motion separately where three frames cannot establish it.

Check the ledger against the recording: named references must receive appropriate
attention on their words; claims must not anticipate the narration. Inspect dense
proofs and all meaningful composition clears across every section.

Check audio separately. Speech recognition and peak measurements do not establish
that a transition sounds natural. Preserve raw takes and sample counts; protect
speech when removing noise from pauses. State any listening limitation or pickup
needed instead of claiming a perceptual audio check that was not performed.

Only after repairs and verification should a note move to `pending_review`, with
a concrete explanation. Only the viewer resolves it. Answer annotation questions
in their threads, and leave unresolved repairs visibly pending. Assemble the full
preview after the section checks; repeat checks only for subsequent changes.
