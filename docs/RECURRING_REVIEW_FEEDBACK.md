# Recurring animation feedback: reference for the agent

The preferred visual style is a carefully built whiteboard explanation. Start
with a useful composition and develop it. Keep useful work visible and move it
when space is needed. A new spoken clause usually calls for a local change,
not another slide.

## Quick reference: recurring complaints and required checks

Use this before handing over a preview. These are recurring failures to prevent,
not suggestions for the author to check again.

| Complaint pattern | What the agent must check |
|---|---|
| Random, early, or late pulses and boxes | Every attention effect has a specific spoken referent. Compare its actual rendered start with that word, including time spent in preceding animations. Remove effects without an instructional reason. |
| The narration names something but the viewer cannot find it | Focus the correct object or term on its reference. Follow the spoken order; retain simultaneous emphasis during an actual comparison. An already clear reveal may provide the attention itself. |
| Answers, parameters, or labels appear before their explanation | Check the first frame in which the content becomes visible, not only a later pulse. Keep destination cells and new values unpopulated until their own reveal or arrival. |
| Too many slides, resets, title changes, or disappearing equations | Compare compositions before and after. Keep useful definitions, proof steps, and unchanged equation terms. Move or regroup existing work to make room; clear it only when the explanation has finished using it. |
| Crowding, overlap, poor alignment, or clipped content | Inspect complete video frames: titles, section markers, labels, formulas, braces, arrows, dividers, and effect outlines. Check spacing and hierarchy as well as intersections. Readability matters even when geometry tests pass. |
| Pop-ins, leftover edges, duplicate labels, or symbol scrambling | Inspect intermediate frames. Nodes and edges share a lifecycle; each visible object has one owner. Travelling copies stay readable, and substitutions finish without reviving old objects. |
| Arbitrary colors or a label contradicting its visual state | Keep the established semantic palette. Update a state value and its styling together. A temporary spoken mention does not justify changing the object's meaning or color. |
| Mathematics changes unexpectedly or a derivation loses its logic | Keep notation, scale, row orientation, braces, and function meaning consistent. Carry definitions to their application. Retain earlier proof work and show where the base case, changing measure, runtime, and requested answer come from. |
| Spoken examples or actions have no useful visual counterpart | Show the concrete instance and demonstrate the described operation. Count states from parameter ranges; do not make picturing an array's dimensions a prerequisite. |
| Audio clicks, shuffling, level jumps, or misleading sound-quality claims | Check edits inside takes as well as between takes. Preserve raw audio, protect speech, and distinguish signal checks from actual listening. Identify specific pickups when noise overlaps speech. |
| Only the selected section is fixed, or notes/replies stay stale | Read notes and follow-ups across every section. Check other uses of the same faulty component. Refresh feedback and transcript data when they change. Agent fixes await review; only the author resolves them. |

When one of these failures occurs, repair the shared component or scheduling
code where appropriate and inspect its other uses. Add a regression check when
the failure is mechanically detectable. Keep new recurring feedback in this
document so it remains available in later sessions.

Record what was actually inspected. An all-section audit, sampled visual review,
continuous playback, and perceptual audio listening are different scopes. Do not
call every frame verified when only selected frames were inspected, and do not
promise that passing checks makes further mistakes impossible.

## Timing and attention

When the narration names two objects in sequence, focus them in that sequence.
When it compares them together, retain the comparison. Use a pulse for an isolated
object, a box for a term within an equation, and an arrow for a relationship.
Use a persistent tint only when the object's meaning or status changes.

An unsupported pulse is an error. Silence is not a reason to animate. A delayed
pulse is also an error: the preceding cue does not excuse time spent in another
animation. A newly revealed object normally already has enough attention.

Do not make the viewer read an unexplained claim early. Reveal the two requested
child calls before expanding the rest of a tree. Introduce a parameter when the
reasoning needs it and the narration names it, not when an illustration happens
to be constructed in code.

## Mathematical continuity

Keep `f(...) =` visible through the English-to-math construction. Preserve row
orientation, font scale, braces, equals signs, and unchanged terms. Use braces
consistently; avoid combining a brace with bullet points for the same choices.

Applying a definition means visibly carrying a copy from the definition to its
use. The source remains. An identical formula should travel intact; its repeated
symbols must not swap places because of differing Manim group structures.

Keep the proof rail and prior reasoning while changing a hypothesis or base case.
Update the affected row in place. Do not fade in a whole replacement proof.
Algebra can reuse one working line when retaining all intermediate equalities
would force tiny text or move the work outside the proof.

## Layout and color

Short, stable topic headings are preferred. Text on screen organizes the argument;
it does not need to repeat every conversational phrase. Local notes belong beside
their targets. Leave enough space for their labels, effects, and connecting edges.

Blue identifies structure or the current state. Yellow identifies an operation
or active choice. Green means known, stored, valid, or complete. Red means
invalid or wasted repeated work. White is neutral; gray is supporting material.
Do not cycle these roles merely to emphasize a spoken mention.

Count possible calls from parameter ranges. Storage may be an array, but its
physical dimensions are not required to derive the recurrence, correctness,
population order, or runtime. Avoid suggesting that visualizing an array is a
prerequisite for understanding dynamic programming.

## Motion and lifecycle

Nodes and their edges move or disappear together. A collapsed subtree leaves no
edges behind. Destination values must not appear before the travelling states
arrive. Do not crossfade unrelated text in the same location or animate cleanup
of absent objects. Check motion as well as the final still frame.

Diagrams should demonstrate the stated action: an empty array fills in its cells;
a recurrence uses its two known values; a rejected item visibly exceeds capacity;
one falling domino makes contact before its neighbor starts and eventually rests.

## Before returning the work

Read all notes, including drafts and follow-ups, across all sections. Apply the
same correction wherever the pattern occurs. Ask yourself whether the problem
is actually solved, using the rendered frames and word-level ledger as evidence.
Do not pass the agent's unresolved diagnostic work to the viewer as a final pass.
