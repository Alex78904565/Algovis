# Recurring animation feedback: reference for the agent

The preferred visual style is a carefully built whiteboard explanation. Start
with a useful composition and develop it. Keep useful work visible and move it
when space is needed. A new spoken clause usually calls for a local change,
not another slide.

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
