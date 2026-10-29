# Recurring animation feedback: reference for the agent

The preferred visual style is a carefully built whiteboard explanation. Start
with a useful composition and develop it. Keep useful work visible and move it
when space is needed. A new spoken clause usually calls for a local change,
not another slide.

## Composition and copy contract

The author wants reusable final-layout classes and automatic transitions. Share
the same object across views to retain it. A deliberate `SlideObject.copy()` has
a new identity, starts at the source, and travels to the new location while the
retained original stays visible. Fork a board for a small substitution instead
of rebuilding its definitions, proof labels or unchanged equation terms.

Planning future layouts must leave the visible board untouched. Check endpoint
bounds and alignment, then inspect the actual encoded transition: no stale text
under moving terms, future destination pop-in, orphan groups, or unnecessary
baseline shifts after a fraction simplifies. Deferred scene mutations require
the renderer to redraw the current composition; final coordinates and ownership
assertions alone cannot catch a stale static background. Keep motion paths and
spoken word timing in the review even when endpoints pass.

Shared timeline checks from the migration:

- Verify the cue's meaning before its timing. Compare the actual visible text or
  action with the first word of the matched phrase. Leading filler can be aligned
  precisely and still reveal an answer too early: "is just zero" starts before
  "zero", and "your car" does not introduce the capacity symbol T. Use the
  measured referent word and its specific occurrence. Inspect the encoded frames
  on both sides of it. For runtime products, retain the final layout but reveal
  each factor and then the result as each is explained. Keep legitimate action
  introductions and copied-definition applications; this is a semantic review,
  not a blanket ban on conjunctions or sentence-level cues.

- Layout containers can already be dissolved into child roots when a section
  handoff is retired. Remove the retiring family's actual artwork, not only its
  old container. Inspect the first move and the later clear: a leftover empty
  Fibonacci row was visible only in the encoded frames. The corrected section
  was checked again; a regression test covers dissolved-container retirement.
- A scale-only attention effect must preserve live paint at intermediate frames,
  including while a different animation changes a computed/duplicate status.
  Checking only the final color misses a distracting temporary color reversal.
- Resolve each verified word once. Nested animation preparation must not add a
  second, frame-rounded wait; delayed phases cannot introduce future labels.
- A phrase cue starts on its first word. For repeated values, anchor each
  reveal to the value word at its own measured time: "and one" starts on
  "and", even when its numeric cue time points to the second "one". Check
  the frames between consecutive reveals as well as after both are visible.
- Test component motion on mixed image/vector groups too. Detached planning must
  support the same artwork as the actual interpolation, without a scene bypass.

These are agent verification and regression checks, not new viewer endorsements.

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
- **Goal-based green/red contrast:** the viewer likes the necklace/toilet-paper
  comparison. Good versus bad takes precedence over every other semantic role;
  preserve that contrast when adding status or attention styling.
- **Knapsack fit condition:** the viewer specifically liked the existing
  condition explanation in clip 7, requesting only `if` and removal of its
  parentheses. Preserve that explanation and its local highlights when fixing
  the notation; this praise does not approve the later proof or worked sums.
- **Copy, substitute, cancel:** the viewer called the refresher's repaired
  definition application "great" and requested an earlier spoken trigger.
  Preserve that specific mathematical motion while changing its cue; the
  praise does not approve other substitutions or their timing.
- **Contact-based domino motion:** the viewer called the repaired fall a
  "phenomenal fix." Preserve its contact geometry and resting positions. Dense
  motion sampling and an explicit geometric model worked for this repair.
- **English beside mathematics:** clip 2's revised explanation received positive
  feedback. Keep its concise English rule as a descriptor below the recurrence,
  following the viewer's latest preference; do not turn it into another slide.
- **Count the relevant objects visibly:** highlighting all tree nodes helped
  distinguish all calls from just the base-case calls. Restore that instructional
  connection when needed; removing unnecessary motion must not remove evidence.
  The latest refinement specifically endorses a persistent tint on the uncounted
  internal nodes during "only some of the times," while the counted base cases
  keep their established color. Preserve that subset distinction.

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
Name the exact intermediate expressions the viewer must retain. A final result
does not satisfy a request to keep the expression immediately after substitution.
Reserve room for that substituted expression and the result together, extending
the equality to the right or using aligned rows. Only nonessential arithmetic
may reuse a working line; lack of space does not override an explicit retention
request. Move supporting work or revise the layout before shrinking the proof.

Place retained equations in their eventual reference or proof rows before new
rows appear. Keeping a base case visible in its old location is not useful if
the induction hypothesis is subsequently written over it. Inspect the waiting
states before its next narrated mention, not only its final position.

## Layout and color

Treat repeated constructions as library objects, not independently drawn
lookalikes. Use the [shared component hierarchy](COMPONENT_ARCHITECTURE.md).
Tree call nodes and array cells share their frame implementation; proofs share
first-line label constraints. Extend these components rather than patching an
individual occurrence. Rebuild and inspect every affected context when a default
changes, preserving the previously successful motion and composition.

Short, stable topic headings are preferred. Text on screen organizes the argument;
it does not need to repeat every conversational phrase. Local notes belong beside
their targets. Leave enough space for their labels, effects, and connecting edges.

Use a shared left edge for related explanations: problem-data and state bands,
the function meaning, its recurrence, its base case, and proof content rows.
Choose the content column before revealing its contents. Do not independently
center each row or let a longer function signature push its first symbol left.
When adding an argument, retain the function's left edge and make room to its
right. An equation continuation may align its equals sign with the preceding
equals sign; that is a deliberate mathematical indent, not another centered row.
Keep short function meanings to one or two left-aligned lines. Inspect the full
composition both before and after argument changes, proof-layout moves, and
later substitutions. An aligned label alone does not establish an aligned row.
Apply this preference across existing sections, not only the section containing
the latest annotation. Record the groups corrected and the layouts deliberately
preserved. Centered standalone diagrams and balanced comparison panels can stay
centered; the related explanatory rows inside a panel still need shared anchors.
Plan with the final populated rows before animating. When a layout needs repair,
compare a few simple sketches, choose the arrangement, and keep its anchors
through the build. Peer equations use one type size; smaller headings, notes,
or diagram labels need an explicit role in the hierarchy. Do not squeeze one
formula to repair a layout that needs more room. Use the reusable column and
typography helpers so later parameter additions cannot silently undo the plan.

Good/bad evaluation overrides every other color meaning: favorable green and
unfavorable red. Next come known/completed status (green), active operation or
choice (yellow), structure or current state (blue), and neutral/supporting
content (white/gray). Thus a valid but poor runtime is red. Without an explicit
negative judgment, a known, stored, valid or complete result can remain green.
Do not cycle these roles merely to emphasize a spoken mention.
The viewer likes the necklace/toilet-paper green/red contrast. Preserve it as
a favorable/unfavorable comparison relative to the thief's stated goal, as
specified in [the visual language](../VISUAL_LANGUAGE.md). It does not establish
that choosing the individually most attractive item is optimal.
Punctuation does not gain an operator or stored-answer color just because its
shape changes. In a parentheses-to-brackets conversion, preserve its neutral
color and let the notation change carry the explanation.

When fixed problem inputs and the current recursive state appear together,
label them INPUTS and STATE explicitly. Use neutral white for fixed quantities
and blue for the current subproblem, rather than assigning both the same blue
and relying on their position. Carry that distinction into the example's item
badges and symbolic arithmetic; a variable's role must not change at the next
equation. Computed valid totals can be green and a failed test red. Preserve the
existing semantic palette instead of introducing a new color for each label.

An omitted sequence must remain visibly omitted when its endpoint appears:
`f(i+3,...) -> ... -> f(n,...)`, not a direct next-step arrow to `f(n,...)`.
Extend a running sum by retaining its existing terms, inserting the new addend,
and updating its result. Do not replace the whole line with a new fade merely
because the total changed. Keep redundant range captions out of a recurrence
when the separately retained base case already makes that distinction clear.

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

  - **Left-aligned does not mean left-heavy.** Measure the completed rows as
    one block and center that block in its allotted region, retaining a common
    left edge inside it. A full-width region is available space, not a reason
    to pin short content to its far left. `ColumnLayout(content_width=...)`
    reserves the final measured width without shrinking or separately centering
    rows. Check both the shared edge and the outer margins.
  - Use compact, deliberate gaps between a definition, its application, and its
    assumption. Reserved future content must not leave unexplained empty bands
    in the completed frame. Inspect the final populated block as a whole.
  - A requested count needs visible counting evidence: number the relevant
    leaves in a clear spatial order, attached to those leaves as they move.
    Keep starting values in the same notation as the recurrence they justify.
  - Label a plotted expression honestly. `exp(n)` conventionally means `e^n`;
    prefer the actual base, such as `phi^n`, and use that same expression on the
    graph. Do not label a reference exponential as an exact operation count.
  - A concept's name is a neutral heading, not a computed answer. Introducing
    "dynamic programming" does not by itself justify success green.
  - "After this phrase" is a timing contract too. Derive the phrase's end from
    verified word times and reserve a real narration pause for its application;
    do not squeeze the copy, substitution, and simplification under the next idea.
    Keep speech samples intact and retime subsequent words/captions/cues together.
    The viewer specifically liked clip 6's rule-copy, substitution, cancellation,
    and simplification sequence; preserve that sequence when repairing its timing.
  - In deferred sequences, check the boundary between phases. The previous
    copy must be adopted and its traveller removed before the next substitution
    begins. Deferring construction alone does not establish one visible owner.
    A clean final frame can hide an old formula underneath the moving one.
    For a copied mathematical rule followed by substitutions, finish the scene
    play before changing its glyphs as well; inspect that actual handoff.
  - Numbered instructions use `1.`, `2.`, and so on. A middle dot is not a list
    separator. Keep this convention across numbered lesson instructions.

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

## Lessons from the second review of sections 1–6

These are failures of the previous checks, not new preferences. Use the concrete
acceptance checks below when repairing the affected scenes and their other uses.

### Check the argument's intermediate steps explicitly

- Keep the numeric example while deriving its general rule. Replacing
  `8 + 5 = 13 = f(7)` with `f(n)` does not explain why the identity holds for
  every input. Show the base-case counts and the child-count addition rule.
- Keep the expression immediately after substituting the induction hypothesis,
  then the final result to its right. Other retained proof rows cannot substitute
  for that missing expression. When applying the result later, replace only
  `1 + 2 + ... + n` and preserve `f(n) =`.
- Distinguish a numerical count from an asymptotic class. `O(n)` supplies neither
  constant one nor a bound at a particular input. For this Fibonacci algorithm,
  derive one addition per entry after the two base cases: `n - 2 <= n` for
  `n >= 2`. That independently justifies at most 191 additions at input 191.
- Label the quantity currently being discussed. Once operations are related to
  calls, explain that the same curve bounds both; do not silently leave the plot
  labeled as a call count while discussing operations. Prefer "base-case calls"
  to undefined "leaves" for this audience.

**Agent check:** list the required expressions and their roles (example, general
rule, substituted expression, final result). Verify their actual coexistence in
the rendered frame. Check the bridge between each pair, not merely their presence
at different times. Count-based preflight warnings do not decide this question.

### Verify prerequisites and the actual start of the thought

- An addition guide must stay absent until both base values exist. Test an actual
  nested fill sequence: a future `Create` or `Transform` target can become visible
  when its outer animation group starts, before its own scheduled turn.
- Choose the spoken thought that introduces the visual. A timestamp on a word
  halfway through the sentence can pass a mechanical check and still be late.
- Compare that intended onset with the first visible change after cleanup and
  other nested actions. A correct cue followed by a half-second exit animation
  does not make the subsequent reveal timely. Legacy cue waits without recorded
  word timing remain unverified, even when the error count is zero.
- Inspect definition transfers around each internal phase: travel, arrival,
  substitution, and adoption. Include adjacent video frames at those boundaries.
  Repeated glyphs and different formula groupings need their own motion check;
  a correct arrival and final frame can conceal a brief symbol swap.

**Agent check:** record the chosen phrase, intended word time, actual first-visible
time, prerequisite state, and internal phase boundaries. Resolve a mismatch before
calling the effect verified. Do not infer the cause of a brief glitch from a
single still; distinguish an observed failure from a suspected implementation cause.

### Retain useful work and retire completed illustrations

- Keep derivations needed for the current reasoning. A graph whose point is
  complete may leave so the active formulas can be regrouped. Retention is about
  continuity of the explanation, not keeping every object forever.
- Place a qualifier beside the statement it qualifies. A base-case explanation
  in a global footer can incorrectly appear to describe the entire proof.
- Keep comparable dependency diagrams in the same orientation. Preserve the
  useful progression from `n` to smaller inputs; show continuation toward an
  example base case consistently in both diagrams.
- Compare rendered letter heights for peer equations. Equal `.scale()` calls on
  different source objects do not guarantee equal visual text size. First ask
  whether the equation needs to move to another composition at all.
- Position related formulas together rather than scattering supporting results
  into arbitrary corners. Keep "SUPPOSE" and its assumed equation on one line
  in the current runtime estimate, as the viewer clarified.
- A spoken mention and a new known status can justify a pulse plus a persistent
  green tint. Removing decorative emphasis must not remove the onset cue for
  the specific smaller input being assumed correct.

**Agent check:** identify the active argument, each retained item's next use, and
the scope of every note. Inspect the complete composition and peer text sizes.
Preserve explicitly praised devices while repairing the local defect.

## Lessons from the knapsack deep dive

These checks come from the viewer's detailed review of section 7. Recording them
does not mean its current animations have been repaired or approved.

- Introduce numerical values when their objects are named. Track weight and value
  together in the concrete example, and visibly undo an attempted choice that
  does not fit. Do not quietly restore example numbers after removing them to
  discuss the general problem.
- Reserve label space using the final populated text. Two short symbols can have
  ample space initially and collide when replaced with indexed numerical data.
  Check the final glyphs and their gap at full-frame size, not only bounding-box
  thresholds or the empty slots. Keep the same reserved positions during filling.
- Refine the English choice locally. Introducing `w` does not justify immediately
  replacing "if it fits" with a complete capacity inequality. Introduce each
  quantity as needed, then translate the condition on the spoken explanation.
  Similarly, reveal an immediate value on its introduction, then pulse that value
  on the later explicit reference.
- Give the problem data, current parameters, and meaning of `f` stable homes.
  Retire completed choice scaffolding to make room for the definition; keep the
  definition available for its later proof and answer extraction. Use existing
  parameter definitions instead of adding competing underbraces and captions.
- Reuse the arithmetic proof's organization: definitions, claim, base case,
  hypothesis, and working step. A short readable hypothesis such as
  "`f(i+1,w')` is correct for every valid `w'`" can replace dense prose. Keep the
  capacity condition when adding the liked take/skip labels. Box the existing
  definition or recurrence when it is referenced rather than repeating it below.
- Show changing arguments inside successive function calls, populated on their
  spoken references. Keep the proposed simpler base case tied to a local change
  in the existing function meaning. Extract the answer by substituting into that
  same function, rather than introducing an unrelated formula layout.
- Reuse the established visual instance for the example distinguishing exhaustive
  recursion from greedy choice. Keep its capacity with its items. Avoid oversized
  branch headings or persistent boxes that compete with the calculation.

**Agent check:** trace each introduced value from its spoken definition to its
use. List what stays in the composition at each refinement, including conditions,
function meaning, and prior proof work. Compare with the earlier successful proof
layout and inspect the whole frame before accepting a local spacing repair.

## Reuse established formats across the lesson

The author explicitly identified reuse of the existing proof structure as a
successful strategy. Prefer the familiar organization before designing another
layout: definitions, claim, base case, induction hypothesis, and inductive step.
Keep label positions, notation, type sizes, and semantic colors consistent.
Shorter later proofs can omit repeated verbal detail while retaining this visual
structure and the particular measure on which their induction depends.

Reuse the established visual grammar for equations and examples too. A new
problem changes the mathematics, not the meaning of a blue input, a green stored
answer, or a two-row choice brace. Introducing another parameter should refine
the arguments while preserving the function name, delimiters, and equality.
When reading an answer from the function's meaning, carry that same call and
substitute the requested inputs locally. Keep an immediate term in place while
refining its remaining-problem term.

**Agent check:** compare each later example with the earlier successful example
of its kind. Name what is reused and why any departure is needed. A new layout
is justified by a different explanatory need, not by being in a new section.
Inspect populated labels and internal substitution phases in the actual video.

Keep that structure in the code as well. If a later animation changes just an
argument, every earlier refinement must preserve the function's separately
addressable name, delimiters, arguments, and equality. A whole-formula transform
can silently destroy those parts and make the next local change replace the
wrong glyphs. Similarly, preparing a future reveal must not change the opacity
of a child already owned by a visible object during the wait for its cue. Reserve
its space, keep the future content detached, and introduce it on the spoken word.
Check the actual frames immediately before the cue as well as after it.

## Lessons from the latest examples and layout review

- **An ellipsis is an omission, not another state.** Do not give it a node
  box, a cell border, or its own recursive children. Leave it between the
  genuine elements it abbreviates. Center vertical continuation dots in the
  clear gap between the last calls and the base-case label, with even space
  above and below.
- **Peer statements keep the same rendered type size.** A numerical application
  of a runtime calculation should not become smaller than its general formula.
  Use the same math scale and reserve space for both. A comparison's headings,
  function calls, and conclusions should have corresponding anchors across
  its two columns; do not shrink one whole argument to make a split layout.
  Register existing equations with `LessonStyle.watch`, not just newly built
  scenes. Retag a deliberate answer/reference hierarchy when the role changes;
  keep new arguments at the call's current size with `math_like`. Verify the
  base case again after it moves into the proof. A second whole-row shrink can
  silently undo an otherwise consistent construction.
- **Keep a small set of familiar layouts.** Center the main equation and its
  parameter-definition block, or align them to an explicit shared column.
  Avoid unrelated labels in opposite corners. A recurrence introduced on one
  line should retain that organization as its terms become mathematical.
- **Examples retain their problem data.** Keep the objective and distance
  definition above a route example. Show edge costs before quoting their sum;
  keep both routes and totals when the explanation compares them. Introduce
  the numerical contribution alongside its symbolic contribution in a worked
  knapsack sum, rather than revealing an unexplained total later.
- **Show the intermediate algebra that explains the result.** When applying
  a rule containing n at k+1, carry down the general rule, let it remain
  readable, substitute k+1, and show the cancellation before simplifying.
  Do not make that reasoning a fleeting morph inside the transfer helper.
  Use the existing `DeferredAnimation` around each later substitution and
  cancellation phase. Otherwise Manim can add a future phase's source while
  the general rule is still being copied or held. The regression test must
  check that future expressions and strike marks are actually absent.
- **Undo the demonstrated action coherently.** An item returned from a bag
  follows the reverse of its insertion path. Inspect the motion, not only its
  final position. Preserve the working item art, capacity feedback, and timing.
- **Neutral headings stay neutral.** Naming dynamic programming in a recap is
  not a completed-result status. Green remains reserved for known, stored,
  valid, selected, or completed work.
- **The recap preserves the general rule's meaning.** Use `combine` in the
  universal recurrence and in its per-choice construction. Addition is justified
  in a particular additive problem; it must not silently replace the general
  operation when summarizing the method. Match notation across the lesson and
  its conclusion as well as across adjacent frames.

**Agent check:** compare the general and concrete calculations at their actual
rendered sizes; inspect the complete split composition and operator baselines.
Trace each example's displayed totals to visible input data. Inspect the hold,
substitution, cancellation, and final adoption separately. Keep established
proof rails and successful local explanatory devices while making these repairs.

## Before returning the work

### Latest proof and runtime review

- Independent clips still form one continuous lesson. Compare the actual last
  frame with the next first frame; do not erase an array or tree at the end and
  redraw it in a different position after the cut. The introduction carries an
  empty Fibonacci row into the calculation. Shared factories own continued
  objects; native `SectionHandoff` artwork carries a completed composition into
  a deliberate topic change. Keep narration on its existing clock and rebuild
  successors when their predecessor's ending changes. A matching cut alone does
  not excuse clearing reasoning that the next sentence still uses. See
  [section continuity](SECTION_CONTINUITY.md).

- Sharing an array primitive is insufficient. The proof rails, developing
  equation columns, cases, comparison frames and chapter markers must also
  instantiate shared implementations. Use `ProofFrame`, `EquationFrame`,
  `CaseEquation`, `PanelFrame`, `ComparisonFrame` and `ChapterMarker`; keep
  their common geometry in `LessonFrameStyle`. Profile differences reserve
  space for the content rather than creating another local visual style.
  Check all dependents when a component changes. The source watcher must
  queue all affected clips, with Manim executions serialized, rather than
  leave earlier clips stale because another section was open.

- Repeated objects must share their implementation, not merely resemble one
  another. Use `StateCell` / `StateRow` for the separated numerical/state rows
  in the introduction, Fibonacci construction, hand calculation, and stored
  array. Keep border, corner, fill, value size, and gap consistent. A miniature
  recap scales the same component. `card()` is a content-sized callout, not an
  array cell. When a component changes, inventory earlier uses too; inspecting
  only the newest section leaves obsolete designs in the finished lesson.
  Keep proof rails, headings, comparison frames, and equation columns on their
  established shared formats unless their different purpose warrants a change.
- A new worked instance reuses the earlier problem's actual cards, artwork,
  names, metric slots, bag and capacity gauge. Changing the numbers is not a
  reason to put metrics outside the cards or omit the gauge. Inspect both
  instances together. Keep take/skip tags in a shared label column, independent
  of how long their mathematical expressions are.
- Write the induction hypothesis as an assumption: "Assume P(k) holds", with
  its implication beneath it when needed. Adjust the index to the proof's
  actual child size. Mark the changing arguments inside the child calls on the
  words explaining progress, rather than briefly boxing the claim instead.
- Typography must survive local substitutions. Build digits and changed calls
  with `LessonStyle.math_like`; matching a numeral's height to a parenthesized
  call makes that numeral too large. Do not resize a whole definition to a
  target width or height when it enters a proof or becomes a reference. Use a
  common scale for the complete reference block and reserve enough room.
  Font-size equality alone is insufficient: centering `0` on `w` or `3` on
  a subscript can lower the replacement. Use `MathRow` for changing arguments
  and worked arithmetic. Plan the complete native TeX row, animate its named
  terms, then commit that layout. Its baseline/spacing contract is checked in
  the actual render manifest before publication. Never repair this by nudging
  a particular digit until it looks approximately right.
- Keep a definition's focus box through the explanation that refers to it.
  Change only the `1` in `P(1)` when it becomes `P(0)`. Make moving beyond the
  last item visible before deriving zero additional value. End a completed
  induction with its quantified conclusion, using the induction variable k.
  Use `focus_on_cue(..., until=...)` for these sustained references. Its next
  spoken cue releases the box; the audit rejects missing, prematurely removed,
  or lingering boxes. When two calls are named, use a separate box around each
  call, excluding the immediate value beside it. Give the assumption and its
  stated consequence equivalent attention on their respective spoken words.
  Show the proof's row labels when entering the proof, rather than leaving an
  already visible base case unnamed until much later. Move retained material
  deliberately; available silence is room for comprehensible movement.
- Changing the meaning of an induction index is a local revision of the
  completed proof. Retain the conclusion and working rows. Update every
  dependent index, base, and quantified statement when showing the alternative;
  restore them together when returning. A backward proof may assume `P(k+1)`
  to prove `P(k)`. Demonstrations about the base belong beside that row, not
  over the proof's conclusion.
- Worked alternatives use the same evaluation grammar. Replace the child
  value first, retain the immediate value, then append the evaluated total.
  For example, `5 + f(2,3)` becomes `5 + 0`, then `5 + 0 = 5`; its peer
  becomes `0 + 6 = 6`. Compare both complete chains before choosing. Declare
  `MathRow.require_sum()` for additive numeric examples so a wrong completed
  equality cannot publish. Inspect every intermediate stage, including the
  spacing of newly inserted operators. Keep helpful take/skip labels with
  the recurrence in construction, proof, and later copies.
- A pause requested after a sentence belongs after its last spoken word.
  `play_on_cue(..., edge="end")` supports that distinction explicitly. Returning
  a rejected item during "so it doesn't fit" is different from returning it
  after those words. Retiming must preserve the raw recording and shift all
  downstream word, cue, and assembly times together.

- Establish a conclusion before extending it. Keep `# base-case calls in
  f(n) = f(n)` readable, then append the total-call inequality when the narration
  explains that these are only some calls. Carry the complete predicate from
  the retained argument. Label a numerical example with its actual input.
- Put an explanatory caption next to its named referent. A note about the
  growth of the upper operation bound belongs beside that bound, not above a
  different expression lower on the slide. Axis labels must remain readable.
- Good/bad evaluation takes precedence over a runtime bound being correctly
  derived. Use red for the impractical recursive runtime and green for the
  improved DP runtime in a performance comparison. Keep headings neutral and
  use the same corresponding colors in plotted series and labels. Color judges
  the stated performance comparison, rather than the correctness of the math.
- In a correctness proof, the desired optimal-value interpretation is part of
  the claim being established. Keep the actual recurrence under definitions.
  Retain the familiar proof rail and place the interpretation with `P(k)`.
- When a claim changes, check its base by carrying the general formula down,
  substituting the base input, and simplifying. Return to the existing base
  row. Substitute into the working equality already on screen rather than
  erasing and re-copying an earlier recursive step.
- For numbered spoken instructions, show the number on “First” or “Step two”
  and its description on the phrase stating the action. A whole condition
  introduced as a condition appears together; separate token introductions
  are useful only when the narration actually derives those tokens.
- Preserve the praised copy/substitute/cancel motion. Its latest requested
  trigger is “except”; the old extra pause after “by definition” is superseded.
  Cue choices belong to the current recording and must not become general
  timing rules. Finish each scene play before mutating copied math glyphs.
- Keep a worked example's complete weight and value calculation visible when
  identifying its best feasible choice. If a requested reading pause is added,
  shift words, cues, captions, and assembly metadata together. Preserve raw
  recordings and reject an insertion point that cuts through voiced speech.

Ready-for-review notes need a repair starting point, separate from the original
annotation evidence. Set `reviewAt` to the first cue where the change is visible;
the viewer should not have to rewind from an old screenshot time to find it.
Retain access to the original note time. Do not overlay its stale selection
rectangle on a layout that has moved. A follow-up reopens the note rather than
silently reusing the previous repair's location.

Preserve the viewer's preflight decisions for unchanged moments. A render name,
source-line change, or edit elsewhere in a section must not reopen every flag.
Record the local rendered evidence and narration when a check is accepted;
reopen it only when that evidence changes. Keep earlier decisions as history.
Do not infer approval of changed content from an old decision without evidence.

Static operation counts are an agent diagnostic, not proof of visual clutter.
A coordinated notation change can manipulate many objects while conveying one
idea. Exclude cleanup from counts of new content and treat explicitly coordinated
builds as a unit. Deduplicate the same concern at the same cue, while keeping
different moments and technical errors distinct. Ask a specific question about
the actual concern instead of repeatedly asking whether a moment looks good.

In a runtime argument, make a numerical sum's symbolic identity explicit before
generalizing it. Distinguish uncounted internal calls from counted base calls
with a persistent structural tint when the narration explains the omission.
Peer formulas should use consistent rendered text sizes; neutral qualifiers
such as SUPPOSE do not acquire the operator color merely to attract attention.

Ask the author early if a note could reasonably require different visual outcomes.
Specific questions are welcome; a long wait followed by a guessed interpretation
is not. Explain the ambiguity concretely and keep working on unaffected repairs.
Use the answer to update this reference when it establishes a reusable preference.

Read all notes, including drafts and follow-ups, across all sections. Apply the
same correction wherever the pattern occurs. Ask yourself whether the problem
is actually solved, using the rendered frames and word-level ledger as evidence.
Do not pass the agent's unresolved diagnostic work to the viewer as a final pass.

Shared safeguards must reach existing production scenes. Installing a helper
or enabling a publication check is not the same as migrating all clips. Keep a
section inventory of editable math, attention lifetimes, and timing coverage;
record when an existing static equation or brief pulse correctly needs no
replacement. Rebuild and inspect the actual dependent compositions.

Local argument substitutions need the complete native mathematical layout.
Do not replace a letter with a centered digit, or manually splice children into
an editable row. Keep semantic term names stable as parameters are introduced.
Worked additions retain their intermediate expression and reveal the total
after the child value, with a numerical consistency check where appropriate.

A repeated phrase can resolve to the same spoken occurrence twice. Coordinate
mechanical continuation as one declared sequence instead of pretending there
are two separate word triggers. Recover estimated mathematical word timing
from the recording or forced alignment of the reviewed wording; retain that
evidence. Do not remove approximation flags to make a strict check pass.

Check the first visible state change, not only the declared animation. Direct
recoloring or unhiding before `play_on_cue` evaluates its arguments can paint
during its wait. Put the verified word wait before that preparation, or animate
the change inside the cued operation. Inspect a frame before the trigger to
confirm the old state is still present.
