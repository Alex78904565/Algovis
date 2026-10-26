# Algovis visual language

This document is the authoritative semantic color convention for the video and
the reusable Algovis components. Color should explain an object's role. It
should not change merely to make a frame look more varied.

## Semantic palette

- **Blue (`theme.primary`) — structure and state.** Inputs, parameters, current
  states, array indices, dependencies, and neutral branches use blue. For
  example, `v_i`, `w_i`, and `C` are all input data and therefore use the same
  blue.
- **Yellow (`theme.accent`) — the decision currently under discussion.** Use it
  for the active choice, optimizer, question, or piece of algebra presently
  receiving attention.
- **Green (`theme.success`) — known, stored, selected, or valid.** Use it for
  computed array cells, cached answers, accepted choices, satisfied
  constraints, and completed DP results.
- **Red (`theme.danger`) — invalid, rejected, or wasteful.** Use it for
  constraint violations, rejected choices, and duplicated work that will be
  eliminated.
- **White (`theme.foreground`) — neutral content.** Ordinary prose, operators,
  and mathematical material without a special semantic role remain white.
- **Gray (`theme.muted`) — scaffolding.** Secondary labels, inactive edges,
  dividers, and supporting explanations use gray.

## Attention without changing meaning

Prefer a temporary outline, underline, arrow, or small scale pulse when the
narration refers to an object whose semantic role has not changed. Do not
permanently recolor it just to direct attention. When an object's role really
does change, such as an empty cell becoming computed, animate it from its old
semantic color to its new one.

## States and storage

A state is an input to the solution function. Count the possible parameter
values to bound the number of states, then multiply by the work for one state.
Brackets explain that an answer is stored; they do not require a drawing of
the storage layout. Use the dependency structure or parameter ranges when
discussing correctness, population order, and runtime. A grid is an optional
concrete illustration, never a prerequisite for understanding more parameters.

## Consistency checks

Applying a definition has a consistent motion: keep the definition visible,
carry a copy to the expression where it is used, and replace only that
expression. The source, surrounding symbols, and semantic colors remain
stable. This also applies when an induction hypothesis supplies a child
call's value. Use `ApplyDefinition` instead of morphing the entire equation.

Before publishing a clip:

1. The same symbol retains the same semantic color across a layout change.
2. Related inputs such as `v_i`, `w_i`, and `C` share the structural blue.
3. Green never means merely “currently mentioned”; it means known, stored,
   selected, valid, or complete.
4. Red never decorates neutral content; it identifies a real error, rejection,
   violation, or repeated waste.
5. A screenshot taken at any point should be interpretable without relying on
   a transient flash to explain the colors.
