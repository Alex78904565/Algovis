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

## Successful patterns to preserve

Record successful choices as well as failures. Keep the evidence level explicit:
the viewer liking a particular device is not approval of every section using it,
and an agent's frame check is not viewer endorsement.

Viewer-endorsed patterns from this lesson's reviews:

- **Minimal introduction:** the topic title and one small, appropriately timed
  character beat. Do not expand it back into a sequence of narrated slogans.
- **Two-input addition lane:** the moving yellow pair box, a plus between the
  inputs, and a short blue storage arrow clear of the box. Reuse this visual
  grammar when another Fibonacci row performs the same addition.
- **Local explanatory notes:** keep "already computed" and "requested again"
  beside the specific nodes they explain, with room for tree edges. Preserve
  this relationship when repairing spacing rather than relocating the notes to
  a detached caption area.
- **Tree compression:** preserve the visible connection between repeated calls,
  surviving states, and storage. In the current narration's tree/array comparison,
  survivors merge into the array below while that already computed row remains.
- **Equations built in place:** keep the function definition and useful work
  visible as the explanation develops. Preserve the existing orientation and
  refine the affected term rather than replacing the whole composition.

Before revising one of these devices, state which part of it is working and which
part needs repair. Preserve the working part, compare the old and new rendered
frames, and record any regression. Keep dated frame evidence and viewer responses
in the private audit record; do not label an entire render approved based on a
positive comment about one feature.

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

Place retained equations in their eventual reference or proof rows before new
rows appear. Keeping a base case visible in its old location is not useful if
the induction hypothesis is subsequently written over it. Inspect the waiting
states before its next narrated mention, not only its final position.

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

Check grouped cleanup as well as direct fades. A `wipe()` is a group of exits;
it must finish before replacement text enters the same space. Do not let nesting
silently turn a clear-before-reveal transition into a crossfade. Preserve the
timing of deliberately authored mixed sequences.

A definition transfer queued after a layout move must copy the definition's
position and size when its own turn begins. Its travelling copy must remain
absent during earlier steps of the sequence. Check an actual nested sequence;
testing a transfer in isolation cannot catch an early copy introduced by its
parent animation group.

When the narration has already introduced and filled an array before comparing it
with the recursion tree, keep that array visible below the tree. The surviving
states should visibly merge into its existing cells. Do not blank the numbers or
remove the row for the handoff; consolidate ownership after arrival without a
visible change. This differs from revealing a destination that has not yet been
introduced: that destination must remain empty until the relevant reveal.

## Lessons from the first three sections

These checks address failures found again after the earlier automated and sampled
frame audits. They apply throughout the lesson. A passing ledger is insufficient.

### Carry the argument, not just an object ID

- Treat an English definition as the beginning of its mathematical definition.
  Move it to make room, then refine its words into notation in the same composition.
  Do not discard it and introduce the same definition on a fresh page.
- Build one concise mathematical line when the point is a mathematical relation.
  For example, develop the base-leaf count and its addition rule into `= f(n)`;
  do not replace that connection with several sentences about Fibonacci numbers.
- Retaining one formula while replacing every surrounding explanation does not
  establish continuity. Check whether the viewer can follow the same argument
  through the change without reconstructing what the screen now means.
- Before changing a whole composition, name the new idea that requires it. A
  paraphrase of the current idea is not a new idea. Prefer extending an existing
  formula or adjusting its layout to making another explanatory slide.

**Agent check:** compare the English definition, intermediate reasoning, and final
formula side by side in the frame ledger. Identify what was reused, what changed,
and why a student needs the change. Inspect adjacent plays together, not just each
play's retained-object fraction.

### Make screen text earn its space

- A caption must identify something ambiguous, express a necessary relationship,
  or retain a conclusion needed later. Being mentioned in the audio is insufficient.
- Remove labels that merely narrate the animation or echo the obvious diagram,
  such as a separate instruction to count leaves when the leaves are already
  being identified and counted.
- Prefer an equality or annotation on the existing mathematical line to a new
  sentence announcing what that equality means.
- State a caveat once. If the retained assumption already says it underestimates
  runtime, do not add another caption saying a real call takes more work.

**Agent check:** hide each supporting caption in the proposed composition. If the
diagram, formula, and voice still convey the point clearly, leave it out. A cue
justifies the time of an event; it does not justify the event's existence.

### Keep quantities and claims consistent

- Choose one name for each measured quantity and keep it. Do not alternate
  between "all recursive calls," `# calls`, and `runtime(n)` as unexplained aliases.
- Calls and runtime are related quantities, not identical notation. Retain the
  call-count argument and introduce the work-per-call assumption at the explicit
  step that connects it to an operation or runtime bound. Keep units clear.
- Distinguish exact equalities, approximations, and asymptotic bounds. A bare
  `growth rate: phi^n` is ambiguous. Use a properly qualified exponential-growth
  statement; do not imply an exact Fibonacci formula.
- Keep upper and lower bounds straight even if a review note uses the other term.
  Counting only base-case leaves gives a lower bound on all calls. Establishing
  that is not a reason to add an unneeded upper-bound analysis.
- Do not introduce extra notation solely to repair a caption. Reuse the quantities
  already established, and expose the reasoning when a genuinely new one is needed.

**Agent check:** list every displayed name, its meaning, units, relation symbol,
and justified claim. Follow each across the whole section and its neighboring
sections. Check mathematical meaning separately from typography and object reuse.

### Verify the visible target, not just its scheduled effect

- Immediately before, during, and after a focus effect, the referenced glyphs must
  remain visible, legible, and correctly layered. A visible node border is not
  evidence that its `f(2)` label is visible.
- Inspect fills, label opacity, object ownership, and draw order when highlighting
  a container. Do not accept a timed pulse on a hidden or covered child label.
- Check the actual rendered target without the review interface's selection box.
  A screenshot annotation outline is not part of the Manim animation.

**Agent check:** use a close view of the rendered target at the event boundary and
midpoint, together with the complete frame. The timing audit currently verifies
declared timing; it does not certify legible glyphs, occlusion, or semantic value.

### Center the composition deliberately and keep plot styling meaningful

- Decide whether the main plot, the complete labeled graph, or a deliberate split
  composition is being centered. Include tick labels and axis labels in the layout,
  but check the visible plotting area's balance separately.
- Moving the curve's steep part toward the center by shifting the entire axes
  right can leave the graph itself visibly off center. Inspect both, preserving
  the honest fixed scale and the intended curve escaping the frame.
- Moving a retained annotation away from a curve must trigger a composition check;
  avoiding that one collision does not certify the revised layout.
- Keep a plotted series one semantic color. Do not turn a growth curve red or
  add an unexplained dot merely because it becomes steep. Introduce a marker
  only when the narration uses that particular point or threshold.

**Agent check:** view the complete graph before, during, and after its draw. Record
the intended alignment and the meaning of each series, marker, and color change.
Keep the graph's instructional purpose distinct from repeating the earlier bound.

### Reopened feedback invalidates the affected signoff

A new report on an already audited behavior reopens that behavior for verification.
Keep a question's explanation distinct from an implemented repair. Record the rule
change immediately, but leave the animation repair pending until it has actually
been made and checked. Do not use an earlier zero-error audit as a reply to new
visual feedback. A repeated audio-noise report also reopens the edit; an earlier
non-speech attenuation is not proof that the remaining noise is gone.

## Before returning the work

Ask the author early if a note could reasonably require different visual outcomes.
Specific questions are welcome; a long wait followed by a guessed interpretation
is not. Explain the ambiguity concretely and keep working on unaffected repairs.
Use the answer to update this reference when it establishes a reusable preference.

Read all notes, including drafts and follow-ups, across all sections. Apply the
same correction wherever the pattern occurs. Ask yourself whether the problem
is actually solved, using the rendered frames and word-level ledger as evidence.
Do not pass the agent's unresolved diagnostic work to the viewer as a final pass.
