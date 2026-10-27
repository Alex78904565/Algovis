# Manim review surface

The review surface always shows a real Manim MP4. The browser does not imitate
or reimplement the scene. Its job is to connect a precise part of that render to
a precise narration cue and a plain-language change request.

## Run the reviewer

From the project folder, run:

```bash
python review_demo.py
algovis-review --catalog examples/review/catalog.json --watch review_demo.py --watch algovis
```

The example generates a real Manim MP4, a selectable-object manifest, and a
silent track beside its sample transcript. It contains no recorded voice or
third-party music. If the command is not on your path, use
`python -m algovis.review.server` with the same arguments.

For another lesson, copy `examples/review/catalog.json` and configure each
section's `source` Python file, `scene` class, `video`, `renderedVideo`, `cues`,
and `transcriptWords`. Paths are relative to `--workspace` (the current folder
by default). The optional `audio` field supplies a mastered narration track;
`music`, `musicTitle`, `musicGainDb`, and `musicOffsetSeconds` configure a
separate music audition. `source` renders directly through Python and Manim
on Windows, macOS, or Linux. The original production's optional PowerShell
launcher remains supported when no source is supplied.

Open the local address printed in the terminal. Then:

1. Choose a video section from the menu in the header.
2. Open **Preflight** to review one flag at a time, in timeline order. Each flag asks a short
   question. **Watch moment** plays the nearby passage and returns to that
   question. **Checked & next** saves your decision and advances; **Request a
   fix** sends the flag and your optional note straight to Codex; **Skip for
   now** saves it for later. The remaining count shows your progress.
3. Read the complete transcript. A gold tick marks the precise spoken cue;
   colored bars show the actual start and end of each Manim animation. Bars in
   separate lanes are animations that overlap in time. Click either a cue or a
   duration bar to seek there. During playback, the currently spoken phrase is
   highlighted and kept in view.
4. Click **Select something to change**.
5. Click a single element or drag over a larger region in the Manim frame.
6. Describe the desired change and save the note.
7. Click **Queue notes for Codex** when the review pass is complete.

The reviewer captures the marked frame automatically; no manual screenshot is
needed. An object-aware Manim render also exports the visible objects and their
bounds over time. A single click therefore saves the actual Manim object ID and
label when one is available. Dragging remains a freeform-region fallback for a
relationship or collection of objects. Press **Escape** or click
**Cancel selection** to leave selection mode.

The music strip auditions the section's planned score alongside the processed
voice-over. **Level** balances the score beneath the narration, while **Timing**
moves its musical entrance earlier or later. The configured sidechain preset
automatically ducks the score beneath speech. These choices are saved with the
review and included when notes are queued.

The review notes and marked frame captures are written beneath the selected
section's folder in `.review/annotations/`. Tell Codex to review the queued
annotations; the timestamp, trigger phrase, selected region, and frame capture
make each request unambiguous.

Click a saved note to open its marked frame and discussion. Click the same note
again to close it. After Codex attempts a fix, the note changes to **ready for
your review**; only the viewer marks it resolved.

Preflight decisions are saved for the flagged moment. Reloading the reviewer,
rerendering identical content, or editing another part of the section keeps the
decision. The reviewer compares the actual decoded video frames and local
narration timings; timing and audio checks also compare the speech. Music and
mix changes reopen audio checks, without reopening unrelated visual checks.
Earlier decisions remain in the local history. Older decisions that have no
moment-level evidence migrate only when their original version still matches.
Adding a change request does not reset the other checks. Use
**Previous**, **Next**, or **Revisit flags** to inspect earlier decisions, and
**Reopen flag** to undo one. Technical errors must be investigated or fixed and
cannot be cleared solely by checking the picture. Ordinary preflight warnings
can be checked off when the preview is correct.
Checking a flag also resolves its linked change request. Resolving that request
also checks the corresponding nontechnical flag for the current moment, so the
same fix does not need to be confirmed twice. Duplicate reports of the same
concern at one cue share a check; different moments stay separate.

Density estimates count independent additions rather than every animation
primitive. Cleanup adds no competing content, and an explicitly coordinated
build counts as one unit. They remain conservative prompts for inspection;
word-timing, continuity, geometry, and technical errors have separate checks.

## Approve a finished section

When the section looks and sounds good, click **Approve section** above the
video. All saved notes must be resolved first. Approval is your editorial
decision; the separate preflight checklist remains available for technical
follow-up.

The section menu shows **Not reviewed**, **Needs review**, or **✓ Approved**,
and the approval bar shows how many sections are done. **Next section** and
the section menu are available without approving anything. Review in whatever
order helps you judge the lesson as a whole. Use **Reopen review** if you
change your mind.

Codex handles the full project queue across every section, including drafts
and follow-up questions. The selected section and approval status do not
limit that work. Approval is final editorial signoff when the section fits
the whole lesson; it is not a request to unlock work on another section.

Approval is saved across restarts and applies to the version you reviewed.
A new render, revised soundtrack or mix, revised cue/transcript data, or changed
review notes marks that section as needing review again. Reloading the page or
running preflight by itself does not reset approval.

## Inspect a change without scrubbing

The **Animation frames** strip shows three frames extracted from the actual
Manim MP4: one just before a change, one halfway through it, and one just after.
Animations running together are grouped into one change so that a transition
with several moving objects is reviewed as a whole.

Use the arrows or the dropdown to choose a change. Click **Before**, **During**,
or **After** to pause the main video at that exact frame; the transcript and
music follow the same timeline. You can then select an object or add a timing
note normally. Manually choosing a change pins its frames in place. **Follow
playback**, or resuming playback, makes the strip follow the video again.

Frames are generated on demand and cached for that render. A new render gets
fresh thumbnails automatically. A section without an animation manifest needs
one review render before its strip becomes available.

## Live rendering

The launcher watches the scene source and reusable Algovis components. After
one changes, it waits briefly and rerenders only the section currently open in
the reviewer. It combines the new Manim video with that section's processed
dialogue, records selectable object bounds and exact animation intervals, and
refreshes the browser at the same timestamp. **Render section** performs the
same operation immediately. A section's duration bars and object-aware
selection become available after that section has received one review render.
Projects can generate a preflight report with `algovis.qa.audit_project` and
save it to `.review/audit.json`; the reviewer refreshes that report
automatically. Storyboards can be authored and validated through
`algovis.storyboard`. The original lesson's optional export/audit adapters
remain supported separately from the general reviewer.

The annotation layer does not need to expose Manim's full collection of knobs.
The user identifies what is wrong and what should change; the source remains the
single source of truth for layout and animation behavior.

Music is optional and no music is bundled. Supply an appropriately licensed
track for a published video.
