# Algovis

## Review animations before rendering

Algovis includes a cue-driven storyboard language for reviewing visual logic
without reading Manim code. Each high-level animation declares one goal, then
lists the spoken phrases that trigger its individual visual components. See
[`docs/ANIMATION_LANGUAGE.md`](../docs/ANIMATION_LANGUAGE.md). The current
Dynamic Programming video is transcribed under
[`storyboards/dynamic_programming`](../storyboards/dynamic_programming).
The mandatory production gates are in
[`docs/ANIMATION_QA_STANDARD.md`](../docs/ANIMATION_QA_STANDARD.md); the review
app displays the generated per-section audit before playback.

Reusable Manim components for algorithm and dynamic-programming explanations.

## Slides and hand-authored videos

Use `SlideScene` for titles, safe content regions, captions, themes, and reliable
transitions. A video can be written as a short sequence of visual beats:

```python
from manim import MathTex
from algovis import SlideScene, WARM_THEME

class MyLesson(SlideScene):
    theme = WARM_THEME

    def construct(self):
        self.begin_slide("Start with a state", "1 · Construct")
        self.show(MathTex(r"f(k,c)"))
        self.caption("What information describes the smaller problem?")

        self.begin_slide("Make a choice", "2 · Recur")
        self.show(MathTex(r"\max\{\text{take},\text{leave}\}"))
```

`SlideLayout` provides `header`, `body`, `footer`, `left`, and `right` safe
regions. `Slide.place()` and `Slide.stack()` fit content into those regions.
`begin_slide()` owns cleanup of the prior slide; `show()`, `caption()`, and
`clear_content()` track the current slide automatically. The drawable objects
remain separate internally so Manim cannot detach nested labels during child
animations.

See `slide_authoring_demo.py` for a complete renderable example.

For complete algorithm lessons, `AlgorithmLessonScene` accepts declarative
`ProblemLesson` specifications:

```python
class MyVideo(AlgorithmLessonScene):
    def construct(self):
        self.teach_solution(KNAPSACK)
        self.teach_solution(ROAD_TRIP)
        self.teach_solution(TSP)

        self.compare_problem(KNAPSACK)
        self.compare_problem(ROAD_TRIP)
        self.compare_problem(TSP)
```

Each `ProblemLesson` contains a `BellmanSpec`, `ProofSpec`, and
`ComparisonSpec`. The library owns the repeated derive/prove/compare animation;
the video file contains the teaching content and order.

### Concrete problem stories

Use `CapacityChoiceStory` when a problem should begin in the physical world
before it becomes an equation. It supplies an illustrated character, item
cards whose weight/value badges can be revealed later, a capacity container
with a live meter, and animated accept/reject transfers:

```python
from algovis import CapacityChoiceStory, StoryDecision, StoryItemSpec

def story(theme):
    return CapacityChoiceStory(
        items=(
            StoryItemSpec("gem", "diamond", 1, 10, icon="jewelry"),
            StoryItemSpec("roll", "toilet paper", 3, 1,
                          icon="toilet_paper"),
        ),
        capacity=3,
        decisions=(
            StoryDecision("gem", True, "The diamond fits."),
            StoryDecision("roll", False, "The roll would overflow the bag."),
        ),
        contrast_keys=("gem", "roll"),
        theme=theme,
    )
```

Set `intro_factory=story` on a `ProblemLesson`. `AlgorithmLessonScene` then
plays the story before `f(...)` appears. The built-in vector icons are
`jewelry`, `laptop`, `cash`, `toilet_paper`, and `box`; authors can pass a
custom `ThiefCharacter` replacement through the `character` argument.

## Bellman-equation derivations

`BellmanDerivation` presents recurrence construction as a repeatable reasoning
process. It names the unknown function, defines its meaning, writes choices in
English, separates each choice into its immediate effect plus the optimal
long-term effect, transforms that long-term term into the same function on the
smaller state produced by the choice, progressively refines that pattern into
problem-specific mathematics, then asks for the base
case, how the function's outputs answer the original question, and population
order. The answer may be a starting-state call or a post-processing expression.

```python
from algovis import BellmanDerivation

derivation = BellmanDerivation(
    name=r"f(\ldots)=\text{best remaining value}",
    meaning="the optimum using items i through n with w weight in the bag",
    choices=["pick item i if it fits", "skip item i"],
    refinements=[
        r"f(\ldots)=\max\{\text{pick},\text{skip}\}",
        r"f(i,w)=\max\{v_i+f(i+1,w+w_i),f(i+1,w)\}",
    ],
    base_case=r"f(n+1,w)=0",
    answer=r"\text{answer}=f(1,0)",
    population_rule="i increases in child calls; populate i downward",
).move_to(DOWN * 0.3)

self.play(derivation.introduce())
self.play(derivation.explain())
self.play(derivation.consider_choices())
self.play(derivation.write_first_equation())
self.play(derivation.refine())
finish, summary = derivation.finish()
self.play(finish)
```

## Video themes

```python
from algovis import DEFAULT_THEME, LIGHT_THEME, WARM_THEME, NIGHTCLUB_THEME

THEME = DEFAULT_THEME.with_colors(
    primary="#9B8CFF",   # headings and primary structure
    accent="#FFB454",    # attention and active choices
    success="#65D18A",   # memoized/resolved states
    danger="#FF6B7A",    # expensive or naive behavior
    background="#0A0D18",
)

THEME.apply(self)  # inside Scene.setup()
```

Theme roles include `background`, `surface`, `foreground`, `primary`, `node`,
`accent`, `success`, `danger`, and `muted`. A project can select its palette
through one `THEME` value and pass that theme to reusable components.

`NIGHTCLUB_THEME` uses a near-black violet background, ultraviolet headings,
neon-magenta attention cues, and electric-cyan resolved states.

## Dynamic-programming tables

```python
from algovis import DPTable, DPWorkflow, CellState

table = DPTable(
    rows=4,
    cols=6,
    row_labels=["0", "1", "2", "3"],
    col_labels=["0", "1", "2", "3", "4", "5"],
)

self.play(table.write_value(1, 2, "7"))
self.play(table.set_cell_state(1, 2, CellState.RESOLVED))
self.play(table.highlight_dependency(
    table.get_cell(2, 3),
    [table.get_cell(1, 2)],
    labels=["take"],
))
self.play(table.traceback([(3, 5), (2, 3), (1, 2)]))
```

`DPWorkflow` coordinates cell states, dependencies, values, and an optional
`PseudocodePanel`. Its population steps are dictionaries with these fields:

- `cell`: required `(row, column)` coordinate
- `value`: required displayed value
- `code_line`: optional zero-based pseudocode line
- `dependencies`: optional list of cell coordinates
- `dependency_labels`: optional labels such as `take` and `leave`

## Parameter state spaces

```python
from algovis import StateSpaceVisualizer

intervals = StateSpaceVisualizer.intervals(n=6)       # (i,j), i <= j
subsets = StateSpaceVisualizer.subsets(range(5))      # 2^n subsets
tsp = StateSpaceVisualizer.tsp(range(4))              # (vertex, v1, v2, v3, v4)
grid = StateSpaceVisualizer.cartesian(range(4), range(7))
```

Use `highlight_state(state)` to focus a state and `count_label(expression)` to
attach a runtime/count expression.

TSP uses explicit binary visit parameters by default, matching the introductory
recurrence. Pass `representation="set"` when a set-based display is preferable.

## Weighted graphs

```python
from algovis import GraphVis

graph = GraphVis(
    ["A", "B", "C"],
    [("A", "B", 4), ("B", "C", 2), ("C", "A", 7)],
    layout="circular",
)
self.play(graph.traverse_path(["A", "B", "C"]))
```

Graphs accept explicit positions through a node dictionary or automatic
`circular` and `grid` layouts. They support weights, directed edges, node
states, edge highlighting, path traversal, and reset animations.

## Synchronized pseudocode

```python
from algovis import PseudocodePanel

code = PseudocodePanel([
    "for state in states:",
    "  dp[state] = recurrence(state)",
    "recover solution",
])
self.play(code.highlight_line(1))
```

## Recursive-tree layers

`RecursiveTree.get_layer_annotations()` creates labels and dashed guides using
the tree's actual node positions. A custom `label_fn(depth, nodes)` can display
call counts, runtime bounds, or any other per-layer information.

See `library_features_demo.py` for complete renderable examples.

## Memoization transformations

`RecursiveTree` accepts a `state_key` function and can now discover repeated
calls with `get_duplicate_groups()`. Use `highlight_duplicates()`,
`show_cache_hit(node_data)`, and `collapse_to_state_graph()` to animate the
transition from a recursive execution tree to one canonical node per state.
Set `node_shape="square"` when calls should read as state cells that can later
be reorganized into an array.

Use `set_state_colors(color_by_key)` to assign one restrained color to every
occurrence of the same recursive input. Matching calls then remain visually
identifiable while repeated branches move onto their retained states.

Pass `level_fn=lambda args: ...` when a teaching scene should align calls by a
semantic quantity instead of recursion depth. For example, `lambda args: 7 -
args[0]` places every Fibonacci call with the same input on the same horizontal
level while preserving the original parent-child edges.

For a slower explanation, `collapse_to_backbone(kept_nodes)` prunes maximal
discarded subtrees one at a time. Equal-state nodes travel onto their retained
counterparts, the edges follow them, and the redundant branch dissolves in
place only after it arrives. The kept nodes must form a connected tree from the
root. Pass `simultaneous=True` for one coordinated collapse, or choose
`order="top_down"` to begin near the root or `order="bottom_up"` to merge the
deepest repeated branches first. `merge_run_time` and `fade_run_time` control
those two beats independently. Use
`get_backbone_collapse_animations(kept_nodes)` when each fold should be
interleaved with another explanation or state update. If moving edges would
cross important labels, pass `move_edges=False`; each discarded branch's lines
then dissolve just before its nodes move.

`RecursionMemoComparison` carries that visual argument through an entire
runtime comparison. Its square recursion nodes reorganize into either a full
two-parameter grid (`storage_layout="grid"`), a sparse current-state-by-pattern
view (`storage_layout="pattern_grid"`), or a one-dimensional row
(`storage_layout="line"`). For states that should not be forced into a visible
array, `storage_layout="compact"` contracts its unique states into the original
depth levels without axes or a new web of edges. `storage_layout="compact_graph"`
adds the surviving dependency edges when that graph remains readable. Use
`axis_labels=(column, row)` only for the array layouts. Repeated occurrences are
highlighted and then recede before the unique states enter the selected view.

## Algorithm comparisons

`AlgorithmComparison` places naive and optimized `PseudocodePanel` instances
side by side, emphasizes selected added lines, synchronizes line execution, and
attaches runtime labels beneath both versions.

`StateReframing` keeps an original state definition beside an alternate one,
including each function's meaning, parameter bound, and resulting runtime. Use
it when the lesson's point is that changing what a state represents changes the
number of possible calls.

`ValueScan` animates answer recovery from a value-indexed formulation. It scans
candidate values from largest to smallest, rejects states whose stored resource
cost exceeds a bound, and reveals the first feasible maximum. Its state labels
are configurable, so it supports either prefix- or suffix-indexed recurrences.

`BitLengthRuntime` supplies the final technical bridge from a numeric bound such
as `C` to its `Theta(log C)`-bit encoding. It progressively reveals the binary
encoding, substitutes `C = 2^(log C)`, and explains the term
"pseudo-polynomial" without making authors hand-place five separate equations.

## Decisions and parameters

`ApplyDefinition(definition, application, result)` carries a copy from a
visible definition to the term where it is used. The definition stays visible;
only the application is replaced. Position `result` first, keeping surrounding
equation terms outside the animation. Pass `None` as the application to fill
a blank part of an equation. This also works for induction hypotheses.

`DecisionFanout` supports fixed or variable choices, branch labels, disabled
choices, selected transitions, and `min`/`max` merge gates.

`StateParameter` displays a bounded discrete parameter. `BinaryStateVector`
groups explicit 0/1 parameters and provides `flip()`, `set_bit()`, and
`show_bounds()` animations for visit-state explanations.
