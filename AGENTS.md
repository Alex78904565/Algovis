# Working on Algovis lessons

Before changing a lesson, read:

- `docs/RECURRING_REVIEW_FEEDBACK.md`
- `docs/ANIMATION_QA_STANDARD.md`
- `docs/ANIMATION_SELF_REVIEW.md`

These are accumulated production requirements. Use them to audit the work;
do not ask the viewer to rediscover the same mistakes in a preliminary render.
Keep recurring feedback in `docs/RECURRING_REVIEW_FEEDBACK.md` up to date. Use
its complaint/check reference before returning work, repair underlying shared
causes where possible, and state the actual scope of visual verification.
For each change, justify what it adds to the explanation. Check continuity of
the argument and notation, not only retained object IDs. Before an attention
effect, verify that its target's actual text remains visible and readable.
Use the focused checks under "Lessons from the first three sections" and
"Lessons from the second review of sections 1–6" in the recurring-feedback
reference; passing the timing ledger does not replace them. Check exact retained
intermediate expressions, visual prerequisites, and each helper's internal phases.
Consult "Successful patterns to preserve" as well. Record positive feedback
with its specific scope and evidence, and preserve the working parts during
repairs. Keep viewer endorsement distinct from the agent's own verification.

Ask promptly when feedback has materially different plausible interpretations.
The author welcomes specific clarification questions. Do not spend a long time
implementing a guess and then present it as the requested fix. State the precise
ambiguity, ask a short question, and continue independent work while awaiting
the answer. Do not repeatedly ask about preferences already established here.

Read queued annotations, drafts, and follow-ups across every section. The
selected section and its approval status do not limit which notes to handle.
Answer questions in their annotation threads. Attempted, verified repairs move
to `pending_review`; only the viewer marks them `resolved`.

Require a specific spoken trigger for an attention effect. Compare its actual
rendered start with the timestamped words, including time consumed by preceding
animations. An inherited cue does not justify a later pulse. Prefer stillness
over an effect without an instructional purpose.

Use `play_on_cue` for new or repaired spoken content reveals and changes.
Load timestamped `transcriptWords` in the narration document. Missing or
approximate word alignment must be repaired from the recording; do not weaken
the check or substitute a guessed time. A render that misses a declared word
must fail before publication, leaving the previous good preview available.

Build explanations in place. Keep useful definitions and prior work, move them
to make room, and apply definitions by carrying a copy to their use. Inspect
composition changes as well as overlap diagnostics. Render sections separately
and inspect transition frames before assembling the complete preview.

Design for extension through the shared library. Read
`docs/COMPONENT_ARCHITECTURE.md` before adding repeated drawing code. Components
own common geometry, alignment and lifecycle; scenes own mathematical content
and narration. Prefer composition for theme/layout choices, subclasses for real
specializations, and separate objects for substantially different meanings. When
extending a shared object, inventory and check its earlier and later uses too.

Generate the word-level animation ledgers and work through their findings
before requesting viewer review. Passing tests or geometry checks alone cannot
certify timing, clarity, motion, or audio quality. Describe verification limits
honestly, especially when perceptual audio inspection is unavailable.

Preserve raw recordings. Keep private lesson audio, music, renders, annotations,
and production sources out of public commits according to the existing ignore
rules. Publish reusable library, reviewer, examples, tests, and documentation.
