"""Reusable visual workflows for runtime analysis and solution recovery."""

from manim import (
    AnimationGroup, Arrow, Create, DOWN, FadeIn, GREEN, Indicate, LaggedStart,
    LEFT, MathTex, RED, RIGHT, RoundedRectangle, SurroundingRectangle, Text,
    TransformFromCopy, UP, VGroup,
)

from .trees import RecursiveTree
from ..theme import DEFAULT_THEME
from ..frames import PanelFrame
from ..utils.effects import Pulse


class RecursionMemoComparison(VGroup):
    """Show a recursion tree beside a compact or indexed unique-state view."""

    def __init__(self, branching_fn, root_args, *, depth_limit=3,
                 tree_label="RECURSION TREE", graph_label="STATE ARRAY · STORAGE VIEW",
                 storage_layout="grid", axis_labels=("second parameter", "first parameter"),
                 theme=DEFAULT_THEME, **tree_kwargs):
        super().__init__()
        self.theme = theme
        self.tree = RecursiveTree(
            branching_fn, root_args, depth_limit=depth_limit,
            node_color=theme.node, node_shape="square", theme=theme,
            **tree_kwargs,
        )
        self.graph = self._build_storage_view(storage_layout, axis_labels)
        # ``scale_to_fit_width(...).scale_to_fit_height(...)`` can enlarge the
        # object again on the second call.  Fit once by the smaller factor so
        # neither half can spill across the frame or central gutter.
        def fit_inside(mobject, width, height):
            factor = min(width / max(mobject.width, 0.001),
                         height / max(mobject.height, 0.001), 1.0)
            mobject.scale(factor)

        fit_inside(self.tree, 5.45, 3.85)
        fit_inside(self.graph, 5.45, 3.85)
        self.tree.move_to(LEFT * 3.18 + DOWN * 0.28)
        self.graph.move_to(RIGHT * 3.18 + DOWN * 0.28)
        self.left_title = Text(tree_label, font_size=16, color=theme.muted)
        self.right_title = Text(graph_label, font_size=16, color=theme.success)
        self.left_title.next_to(self.tree, UP, buff=0.18)
        self.right_title.next_to(self.graph, UP, buff=0.18)
        # Destination cells are deliberately not children of the visible
        # graph before their animations begin. TransformFromCopy will add each
        # one at its source-tree position and move it into place; keeping them
        # in the graph, even at zero opacity, lets Manim expose their final
        # state while initializing a grouped animation.
        self.arrived_cells = self.graph.cells
        self.graph.remove(self.arrived_cells)
        self.add(self.tree, self.graph, self.left_title, self.right_title)

    def _build_storage_view(self, layout, axis_labels):
        """Arrange one canonical square per state in the requested view."""
        groups = self.tree.get_duplicate_groups(include_singletons=True)
        graph = VGroup()
        graph.nodes = {}
        graph.edges = VGroup()
        cells = VGroup()
        keys = list(groups)
        if layout == "line":
            ordered = sorted(keys, key=lambda key: key[0])
            for key in ordered:
                cell = groups[key][0]["mobject"].copy()
                graph.nodes[key] = cell
                cells.add(cell)
            cells.arrange(RIGHT, buff=0.02)
        elif layout in ("compact", "compact_graph"):
            depths = {}
            for node_data, depth in self.tree.iter_nodes():
                key = self.tree.state_key(node_data["args"])
                depths[key] = min(depths.get(key, depth), depth)
            levels = {}
            for key in keys:
                levels.setdefault(depths[key], []).append(key)
            level_rows = VGroup()
            for depth, level_keys in sorted(levels.items()):
                level_cells = VGroup()
                for key in sorted(level_keys, key=str):
                    cell = groups[key][0]["mobject"].copy()
                    graph.nodes[key] = cell
                    cells.add(cell)
                    level_cells.add(cell)
                level_cells.arrange(RIGHT, buff=0.10)
                level_rows.add(level_cells)
            level_rows.arrange(DOWN, buff=0.14).move_to([0, 0, 0])
            if layout == "compact_graph":
                seen_edges = set()
                for parent, _depth in self.tree.iter_nodes():
                    parent_key = self.tree.state_key(parent["args"])
                    for child in parent["children"]:
                        child_key = self.tree.state_key(child["args"])
                        pair = (parent_key, child_key)
                        if pair in seen_edges:
                            continue
                        seen_edges.add(pair)
                        start = graph.nodes[parent_key]
                        end = graph.nodes[child_key]
                        delta = end.get_center() - start.get_center()
                        graph.edges.add(Arrow(
                            start[0].get_boundary_point(delta),
                            end[0].get_boundary_point(-delta),
                            buff=0.02, color=self.theme.muted, stroke_width=1.5,
                            max_tip_length_to_length_ratio=0.10,
                        ))
        else:
            row_values = sorted({key[0] for key in keys}, key=str)
            col_values = sorted({key[1] for key in keys}, key=str)
            max_side = max(max(groups[key][0]["mobject"].width,
                               groups[key][0]["mobject"].height) for key in keys)
            x_step = max_side + 0.08
            y_step = max_side + 0.08
            slots = VGroup()
            if layout == "grid":
                for row in range(len(row_values)):
                    for col in range(len(col_values)):
                        slot = RoundedRectangle(
                            width=max_side, height=max_side,
                            corner_radius=min(0.06, max_side * 0.1),
                            color=self.theme.muted, stroke_width=1.2,
                            stroke_opacity=0.24,
                        )
                        slot.move_to(RIGHT * col * x_step + DOWN * row * y_step)
                        slots.add(slot)
            for key in keys:
                cell = groups[key][0]["mobject"].copy()
                row = row_values.index(key[0])
                col = col_values.index(key[1])
                cell.move_to(RIGHT * col * x_step + DOWN * row * y_step)
                graph.nodes[key] = cell
                cells.add(cell)
            layout_group = VGroup(slots, cells) if layout == "grid" else cells
            layout_group.move_to([0, 0, 0])
            graph.slots = slots
        if not hasattr(graph, "slots"):
            graph.slots = VGroup()
        graph.add(graph.edges, graph.slots, cells)
        graph.cells = cells
        if layout not in ("line", "compact", "compact_graph"):
            column_text, row_text = axis_labels
            def axis_label(value):
                if "\\" in value or "_" in value:
                    return MathTex(value, font_size=22, color=self.theme.muted)
                return Text(value, font_size=14, color=self.theme.muted)

            column = axis_label(column_text)
            column.next_to(cells, UP, buff=0.12)
            row = axis_label(row_text).rotate(1.5708)
            row.next_to(cells, LEFT, buff=0.12)
            graph.axes = VGroup(column, row)
            graph.add(graph.axes)
        else:
            graph.axes = VGroup()
        graph.source_by_key = {key: groups[key][0]["mobject"] for key in keys}
        return graph

    def reveal_tree(self):
        self.right_title.set_opacity(0)
        return AnimationGroup(FadeIn(self.left_title), self.tree.get_unroll_anim(0.08))

    def highlight_duplicates(self):
        """Highlight repeated calls as a separate, conflict-free scene beat."""
        return self.tree.highlight_duplicates()

    def reveal_memoized(self):
        # Move a copy of each first occurrence into its unique-state position;
        # repeated occurrences recede while one canonical cell per state moves
        # into the selected compact or indexed layout.
        duplicate_extras = VGroup(*[
            node["mobject"]
            for group in self.tree.get_duplicate_groups().values()
            for node in group[1:]
        ])
        discarded_ids = {id(node) for node in duplicate_extras}
        duplicate_edges = VGroup()
        for parent, _depth in self.tree.iter_nodes():
            for child, edge in zip(parent["children"], parent["edges"]):
                if (id(parent["mobject"]) in discarded_ids or
                        id(child["mobject"]) in discarded_ids):
                    duplicate_edges.add(edge)
        state_arrivals = []
        for key, target in self.graph.nodes.items():
            target[0].set_color(self.theme.success).set_fill(
                self.theme.success, opacity=0.16,
            )
            state_arrivals.append(TransformFromCopy(
                self.graph.source_by_key[key], target,
            ))
        organize = AnimationGroup(
            duplicate_extras.animate.set_opacity(0.10),
            duplicate_edges.animate.set_opacity(0.10),
            self.right_title.animate.set_opacity(1),
            FadeIn(VGroup(self.graph.axes, self.graph.slots)),
            FadeIn(self.graph.edges),
            *state_arrivals,
            # TransformFromCopy is an introducing animation. Delaying those
            # animations inside an AnimationGroup makes Manim add every copy
            # at its destination before its scheduled start, which reads as a
            # pop-in. Starting the arrivals together keeps every cell in
            # continuous motion from tree to storage.
            lag_ratio=0,
        )
        return organize


class StateReframing(VGroup):
    """Compare two valid state definitions and the bounds they induce.

    This is deliberately a semantic comparison rather than a table.  It keeps
    the function meaning, parameter range, and resulting state count together
    so a reparameterization never looks like an unexplained symbol swap.
    """

    def __init__(self, *, original_tex, alternate_tex, original_meaning,
                 alternate_meaning, original_bound, alternate_bound,
                 original_runtime, alternate_runtime,
                 labels=("ORIGINAL STATE", "ALTERNATE STATE"),
                 panel_width=5.35, theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme

        def card(label, equation, meaning, bound, runtime):
            frame = PanelFrame(panel_width, 3.45, theme=theme)
            heading = Text(label, font_size=16, color=theme.foreground)
            formula = MathTex(equation, color=theme.primary).scale(0.82)
            explanation = Text(
                meaning, font_size=19, color=theme.foreground,
                line_spacing=0.9,
            )
            explanation.scale_to_fit_width(min(panel_width - 0.55, explanation.width))
            domain = MathTex(bound, color=theme.primary).scale(0.72) if bound else None
            cost = MathTex(runtime, color=theme.success).scale(0.86) if runtime else None
            body = VGroup(heading, formula, explanation,
                          *[part for part in (domain, cost) if part is not None]).arrange(
                DOWN, buff=0.25,
            )
            body.scale_to_fit_width(min(panel_width - 0.52, body.width))
            body.move_to(frame)
            result = VGroup(frame, body)
            result.heading = heading
            result.equation = formula
            result.meaning = explanation
            result.bound = domain
            result.runtime = cost
            return result

        self.original = card(
            labels[0], original_tex, original_meaning, original_bound,
            original_runtime,
        )
        self.alternate = card(
            labels[1], alternate_tex, alternate_meaning, alternate_bound,
            alternate_runtime,
        )
        self.cards = VGroup(self.original, self.alternate).arrange(
            RIGHT, buff=0.55, aligned_edge=UP,
        )
        self.add(self.cards)

    def reveal_original(self):
        return FadeIn(self.original, shift=RIGHT * 0.10)

    def reveal_alternate(self):
        return FadeIn(self.alternate, shift=LEFT * 0.10)

    def highlight_changed_bounds(self):
        return AnimationGroup(
            *[Pulse(card.bound) for card in self.cards if card.bound is not None],
            lag_ratio=0.25,
        )

    def highlight_runtime_tradeoff(self):
        return AnimationGroup(
            *[Pulse(card.runtime) for card in self.cards if card.runtime is not None],
            lag_ratio=0.25,
        )


class ValueScan(VGroup):
    """Scan value-indexed states from high value to the first feasible one.

    ``costs`` may represent weight, time, price, or any resource that must stay
    below ``bound``.  The state and bound labels are configurable so the same
    visual works for suffix- or prefix-indexed formulations.
    """

    def __init__(self, values, costs, bound, *, state_formatter=None,
                 value_symbol="v", bound_symbol="C", result_tex=None,
                 theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        if len(values) != len(costs):
            raise ValueError("values and costs must have equal length")
        self.theme = theme
        self.bound = bound
        self.value_symbol = value_symbol
        state_formatter = state_formatter or (
            lambda value, cost: rf"f(1,{value})={cost}"
        )
        self.cells = VGroup()
        for value, cost in zip(values, costs):
            cell = VGroup(
                MathTex(rf"{value_symbol}={value}"),
                MathTex(state_formatter(value, cost)),
            ).arrange(DOWN, buff=0.12)
            box = SurroundingRectangle(cell, color=theme.muted, buff=0.13)
            cell = VGroup(box, cell)
            cell.value = value
            cell.cost = cost
            self.cells.add(cell)
        self.cells.arrange(RIGHT, buff=0.18)
        if self.cells.width > 11.5:
            self.cells.scale_to_fit_width(11.5)
        self.bound_label = MathTex(
            rf"{bound_symbol}={bound}", color=theme.accent,
        )
        self.bound_label.next_to(self.cells, UP, buff=0.35)
        self.result = MathTex(
            result_tex or
            rf"\max\{{{value_symbol}\mid f(1,{value_symbol})\le {bound_symbol}\}}",
            color=theme.success,
        ).scale(0.78)
        self.result.next_to(self.cells, DOWN, buff=0.36)
        self.result.set_opacity(0)
        self.selected_cell = None
        self.add(self.cells, self.bound_label, self.result)

    def reveal(self):
        return LaggedStart(FadeIn(self.bound_label), *[FadeIn(c) for c in self.cells],
                           lag_ratio=0.10)

    def scan(self):
        animations = []
        for cell in reversed(self.cells):
            feasible = cell.cost <= self.bound
            color = self.theme.success if feasible else self.theme.danger
            animations.append(cell[0].animate.set_color(color).set_stroke(width=4))
            if feasible:
                self.selected_cell = cell
                break
        return LaggedStart(*animations, lag_ratio=0.35)

    def reveal_result(self, *, trigger=None):
        """Reveal the maximization after the scan has found a feasible state."""
        animations = [self.result.animate.set_opacity(1)]
        if self.selected_cell is not None:
            animations.insert(0, Pulse(self.selected_cell, trigger=trigger,
                                      reason="Identify the selected feasible value"))
        return AnimationGroup(*animations, lag_ratio=0.20)


class BitLengthRuntime(VGroup):
    """Explain why a numeric-parameter runtime can be pseudo-polynomial."""

    def __init__(self, *, runtime_tex=r"O(nC)", parameter="C",
                 parallel_runtime_tex=r"O(nV)", parallel_parameter="V",
                 theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        self.runtimes = VGroup(
            MathTex(runtime_tex, color=theme.success),
            Text("and", font_size=17, color=theme.muted),
            MathTex(parallel_runtime_tex, color=theme.success),
        ).arrange(RIGHT, buff=0.18)
        self.encoding = VGroup(
            MathTex(rf"{parameter}=(110101\ldots)_2", color=theme.foreground),
            MathTex(
                rf"\underbrace{{\phantom{{(110101\ldots)_2}}}}_"
                rf"{{\Theta(\log_2 {parameter})\ \mathrm{{bits}}}}",
                color=theme.primary,
            ),
        ).arrange(DOWN, buff=0.03)
        self.substitution = MathTex(
            rf"{parameter}=2^{{\log_2 {parameter}}}",
            color=theme.foreground,
        )
        self.rewritten = MathTex(
            rf"{runtime_tex}=" + runtime_tex.replace(
                parameter, rf"2^{{\log_2 {parameter}}}", 1,
            ),
            color=theme.success,
        ).scale(0.82)
        self.warning = Text(
            f"polynomial in numeric {parameter} · potentially exponential in its bit length",
            font_size=18, color=theme.foreground,
        )
        self.parallel = Text(
            f"The same reasoning applies to {parallel_parameter}.",
            font_size=20, color=theme.muted,
        )
        self.body = VGroup(
            self.encoding, self.substitution, self.rewritten,
            self.warning, self.parallel,
        ).arrange(DOWN, buff=0.23)
        self.content = VGroup(self.runtimes, self.body).arrange(DOWN, buff=0.38)
        self.add(self.content)

        for part in (
            self.encoding, self.substitution, self.rewritten,
            self.warning, self.parallel,
        ):
            part.set_opacity(0)

    def reveal_runtimes(self):
        return FadeIn(self.runtimes)

    def reveal_encoding(self):
        return self.encoding.animate.set_opacity(1)

    def reveal_substitution(self):
        return self.substitution.animate.set_opacity(1)

    def reveal_rewritten_runtime(self):
        return self.rewritten.animate.set_opacity(1)

    def reveal_warning(self):
        return self.warning.animate.set_opacity(1)

    def transfer_to_parallel_parameter(self):
        return self.parallel.animate.set_opacity(1)


class ChoiceRecovery(VGroup):
    """Trace stored states and collect the choices that attained the optimum."""

    def __init__(self, states, choices, *, solution_label="RECOVERED CHOICES",
                 theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        if len(states) != len(choices) + 1:
            raise ValueError("ChoiceRecovery needs one more state than choice")
        self.theme = theme
        self.nodes = VGroup(*[
            VGroup(SurroundingRectangle(MathTex(state), color=theme.success, buff=0.13),
                   MathTex(state)) for state in states
        ])
        # Rebuild boxes around their own labels after construction.
        for node in self.nodes:
            node[0].surround(node[1], buff=0.13)
        self.nodes.arrange(DOWN, buff=0.42).move_to(LEFT * 2.1)
        self.arrows = VGroup(*[
            Arrow(a.get_bottom(), b.get_top(), buff=0.06, color=theme.accent)
            for a, b in zip(self.nodes, self.nodes[1:])
        ])
        label = Text(solution_label, font_size=16, color=theme.muted)
        rendered_choices = []
        for choice in choices:
            line = Text(choice, font_size=18, color=theme.accent)
            if line.width > 5.5:
                line.scale_to_fit_width(5.5)
            rendered_choices.append(line)
        self.choice_lines = VGroup(*rendered_choices).arrange(
            DOWN, aligned_edge=LEFT, buff=0.28
        )
        self.solution = VGroup(label, self.choice_lines).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        self.solution.move_to(RIGHT * 2.7)
        self.add(self.nodes, self.arrows, self.solution)

    def reveal(self):
        self.arrows.set_opacity(0)
        self.solution.set_opacity(0)
        return LaggedStart(*[FadeIn(node) for node in self.nodes], lag_ratio=0.12)

    def trace(self):
        return LaggedStart(
            self.solution[0].animate.set_opacity(1),
            *[AnimationGroup(Create(arrow), choice.animate.set_opacity(1))
              for arrow, choice in zip(self.arrows, self.choice_lines)],
            lag_ratio=0.22,
        )
