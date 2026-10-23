from manim import *
import enum
import numpy as np

from ..theme import DEFAULT_THEME

class NodeState(enum.Enum):
    PENDING = 1
    ACTIVE = 2
    RESOLVED = 3

class RecursiveTree(VGroup):
    """
    A tree that builds itself based on a recursive rule and tracks evaluation states.
    """
    def __init__(self, branching_fn, root_args, depth_limit=5, height=1.15,
                 width=1.15, node_radius=0.34, label_scale=0.58,
                 node_padding=0.12, node_factory=None, node_color=None,
                 state_key=None, node_shape="circle",
                 theme=DEFAULT_THEME,
                 **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        self.branching_fn = branching_fn
        self.depth_limit = depth_limit
        # ``width`` and ``height`` are geometry properties owned by Manim.
        # Keep layout spacing under distinct names or all nodes collapse.
        self.level_spacing = height
        self.sibling_spacing = width
        self.node_radius = node_radius
        self.label_scale = label_scale
        self.node_padding = node_padding
        self.node_factory = node_factory
        self.node_color = node_color or theme.node
        self.node_shape = node_shape
        self.state_key = state_key or (lambda args: tuple(args))
        self.memoized_graph = None
        self.nodes = VGroup()
        self.edges = VGroup()

        # Build hierarchy tree data structure
        self.tree_structure = self._build_node_data(root_args, 0)

        # A fixed center-to-center gap works only while every node has roughly
        # the same small label.  State-heavy labels (notably TSP visit bits)
        # make square nodes taller, so derive a safe center position for each
        # layer from the actual rendered node heights.
        level_heights = {}
        def measure_levels(node_data, depth):
            level_heights[depth] = max(
                level_heights.get(depth, 0), node_data["mobject"].height,
            )
            for child in node_data["children"]:
                measure_levels(child, depth + 1)
        measure_levels(self.tree_structure, 0)
        self.level_y_positions = {0: 0.0}
        for depth in range(1, max(level_heights, default=0) + 1):
            minimum_spacing = (
                level_heights[depth - 1] / 2
                + level_heights[depth] / 2
                + 0.16
            )
            center_spacing = max(self.level_spacing, minimum_spacing)
            self.level_y_positions[depth] = (
                self.level_y_positions[depth - 1] - center_spacing
            )

        # Position nodes relative to root at (0, 0, 0)
        self._position_nodes(self.tree_structure, x=0, depth=0)

        # Draw edges first, then nodes, so lines never cut through circles/text.
        self._create_edges(self.tree_structure)
        self.add(self.edges, self.nodes)

    def _build_node_data(self, args, depth):
        label_str, child_args = self.branching_fn(*args)

        label = MathTex(label_str, color=self.theme.foreground).scale(self.label_scale)
        if self.node_factory is None:
            # Fixed-radius nodes clipped wider labels such as f(12).  Treat the
            # configured radius as a minimum and grow to fit the rendered label.
            radius = max(
                self.node_radius,
                label.width / 2 + self.node_padding,
                label.height / 2 + self.node_padding,
            )
            if self.node_shape == "square":
                side = 2 * radius
                node_shape = RoundedRectangle(
                    width=side, height=side, corner_radius=min(0.08, side * 0.12),
                    color=self.node_color, stroke_width=2.5,
                ).set_fill(self.theme.background, opacity=0.92)
            else:
                node_shape = Circle(
                    radius=radius,
                    color=self.node_color,
                    stroke_width=2.5,
                ).set_fill(self.theme.background, opacity=0.92)
        else:
            node_shape = self.node_factory(label_str, label)
        node_mobject = VGroup(node_shape, label)

        self.nodes.add(node_mobject)

        node_data = {
            "args": args,
            "mobject": node_mobject,
            # Keep ``circle`` as a compatibility alias for existing scenes.
            "circle": node_shape,
            "shape": node_shape,
            "label": label,
            "state": NodeState.PENDING,
            "children": [],
            "edges": []
        }

        if depth < self.depth_limit and child_args:
            for c_args in child_args:
                child_data = self._build_node_data(c_args, depth + 1)
                node_data["children"].append(child_data)

        return node_data

    def _get_subtree_width(self, node_data):
        if not node_data["children"]:
            return max(self.sibling_spacing, node_data["mobject"].width + 0.18)
        children_width = sum(self._get_subtree_width(c) for c in node_data["children"])
        return max(children_width, node_data["mobject"].width + 0.18)

    def _position_nodes(self, node_data, x, depth):
        y = self.level_y_positions.get(depth, -depth * self.level_spacing)
        node_data["mobject"].move_to([x, y, 0])

        if not node_data["children"]:
            return

        total_width = sum(self._get_subtree_width(c) for c in node_data["children"])
        current_x = x - total_width / 2.0

        for child in node_data["children"]:
            child_width = self._get_subtree_width(child)
            child_x = current_x + child_width / 2.0
            self._position_nodes(child, child_x, depth + 1)
            current_x += child_width

    def _create_edges(self, node_data):
        for child in node_data["children"]:
            direction = child["shape"].get_center() - node_data["shape"].get_center()
            edge = Line(
                node_data["shape"].get_boundary_point(direction),
                child["shape"].get_boundary_point(-direction),
                color=self.theme.muted,
                stroke_width=2,
            )
            node_data["edges"].append(edge)
            self.edges.add(edge)

            self._create_edges(child)

    def iter_nodes(self):
        """Yield ``(node_data, depth)`` pairs in preorder."""
        def walk(node_data, depth):
            yield node_data, depth
            for child in node_data["children"]:
                yield from walk(child, depth + 1)

        yield from walk(self.tree_structure, 0)

    def get_layers(self):
        """Return node-data lists grouped by depth, from root to leaves."""
        layers = []
        for node_data, depth in self.iter_nodes():
            while len(layers) <= depth:
                layers.append([])
            layers[depth].append(node_data)
        return layers

    def get_duplicate_groups(self, include_singletons=False):
        """Group node data by recursive state, preserving first-seen order."""
        groups = {}
        for node_data, _depth in self.iter_nodes():
            key = self.state_key(node_data["args"])
            groups.setdefault(key, []).append(node_data)
        return {
            key: nodes for key, nodes in groups.items()
            if include_singletons or len(nodes) > 1
        }

    def _subtree_parts(self, node_data):
        """Return the visible nodes and edges belonging to one subtree."""
        nodes = VGroup()
        edges = VGroup()

        def walk(current):
            nodes.add(current["mobject"])
            badge = current.get("cache_badge")
            if badge is not None:
                nodes.add(badge)
            for child, edge in zip(current["children"], current["edges"]):
                edges.add(edge)
                walk(child)

        walk(node_data)
        return nodes, edges

    def get_backbone_collapse_steps(self, kept_nodes, order="top_down"):
        """Describe the maximal subtrees that can be removed around a backbone.

        ``kept_nodes`` must contain the root and every ancestor needed to reach
        another kept node. Each returned step is a disjoint subtree, so an
        author can remove repeated work one branch at a time without fading a
        child twice. When the discarded root has the same state as a kept node,
        that node is exposed as ``canonical`` for cache-hit highlighting.
        """
        kept_nodes = list(kept_nodes)
        kept_ids = {id(node) for node in kept_nodes}
        all_nodes = list(self.iter_nodes())
        node_by_id = {id(node): node for node, _depth in all_nodes}
        depth_by_id = {id(node): depth for node, depth in all_nodes}
        parent_by_id = {}
        incoming_edge_by_id = {}
        for parent, _depth in all_nodes:
            for child, edge in zip(parent["children"], parent["edges"]):
                parent_by_id[id(child)] = parent
                incoming_edge_by_id[id(child)] = edge

        unknown = kept_ids.difference(node_by_id)
        if unknown:
            raise ValueError("Every kept node must belong to this RecursiveTree")
        if id(self.tree_structure) not in kept_ids:
            raise ValueError("The root must be included in kept_nodes")
        for node in kept_nodes:
            parent = parent_by_id.get(id(node))
            if parent is not None and id(parent) not in kept_ids:
                raise ValueError(
                    "kept_nodes must form a connected backbone from the root"
                )

        canonical_by_key = {}
        for node, _depth in all_nodes:
            if id(node) in kept_ids:
                canonical_by_key.setdefault(self.state_key(node["args"]), node)

        steps = []

        def visit(current):
            for child in current["children"]:
                if id(child) in kept_ids:
                    visit(child)
                    continue
                nodes, internal_edges = self._subtree_parts(child)
                incoming = incoming_edge_by_id[id(child)]
                steps.append({
                    "root": child,
                    "parent": current,
                    "incoming_edge": incoming,
                    "canonical": canonical_by_key.get(
                        self.state_key(child["args"])
                    ),
                    "nodes": nodes,
                    "edges": VGroup(incoming, *internal_edges),
                    "depth": depth_by_id[id(child)],
                })

        visit(self.tree_structure)
        if order == "bottom_up":
            steps.reverse()
        elif order != "top_down":
            raise ValueError("order must be 'top_down' or 'bottom_up'")
        return steps

    def collapse_to_backbone(
        self,
        kept_nodes,
        *,
        order="top_down",
        merge_run_time=0.52,
        settle_run_time=0.12,
    ):
        """Merge discarded work into kept states, one subtree at a time.

        Equal-state nodes travel onto their canonical kept nodes, while the
        branch edges follow their corresponding endpoints. Once the two
        computations overlap, the redundant copy dissolves. This makes the
        visual argument "these calls are the same" rather than merely erasing
        the extra branch.
        """
        kept_nodes = list(kept_nodes)
        canonical_by_key = {}
        for node in kept_nodes:
            canonical_by_key.setdefault(self.state_key(node["args"]), node)

        def edge_target(edge, parent_target, child_target):
            target = edge.copy()
            direction = (
                child_target["shape"].get_center()
                - parent_target["shape"].get_center()
            )
            if np.linalg.norm(direction) < 1e-8:
                return None
            target.put_start_and_end_on(
                parent_target["shape"].get_boundary_point(direction),
                child_target["shape"].get_boundary_point(-direction),
            )
            return target

        animations = []
        for step in self.get_backbone_collapse_steps(kept_nodes, order=order):
            root_target = step["canonical"]
            destination = (
                root_target["mobject"].get_center()
                if root_target is not None
                else step["root"]["mobject"].get_center()
            )
            merge_animations = []

            def merge_node(current, parent=None, incoming_edge=None):
                current_target = canonical_by_key.get(
                    self.state_key(current["args"])
                )
                if current_target is not None:
                    merge_animations.append(Transform(
                        current["mobject"], current_target["mobject"].copy(),
                    ))
                else:
                    merge_animations.append(
                        current["mobject"].animate.move_to(destination).scale(0.25)
                    )

                badge = current.get("cache_badge")
                if badge is not None:
                    badge_destination = (
                        current_target["mobject"].get_center()
                        if current_target is not None else destination
                    )
                    merge_animations.append(
                        badge.animate.move_to(badge_destination).scale(0.35)
                    )

                if incoming_edge is not None:
                    parent_target = canonical_by_key.get(
                        self.state_key(parent["args"])
                    )
                    target_edge = None
                    if parent_target is not None and current_target is not None:
                        target_edge = edge_target(
                            incoming_edge, parent_target, current_target,
                        )
                    if target_edge is not None:
                        merge_animations.append(Transform(
                            incoming_edge, target_edge,
                        ))
                    else:
                        merge_animations.append(
                            incoming_edge.animate.move_to(destination).scale(0.25)
                        )

                for child, edge in zip(current["children"], current["edges"]):
                    merge_node(child, current, edge)

            merge_node(step["root"], step["parent"], step["incoming_edge"])
            subtree = VGroup(step["edges"], step["nodes"])
            animations.append(Succession(
                AnimationGroup(
                    *merge_animations, lag_ratio=0, run_time=merge_run_time,
                ),
                FadeOut(subtree, run_time=settle_run_time),
            ))
        return Succession(*animations) if animations else Wait(0)

    def highlight_duplicates(self, colors=None, opacity=0.28):
        """Color every repeated state consistently across the recursion tree."""
        # Repeated calls all mean the same thing: wasted work.  A rainbow
        # palette made color identify arbitrary groups instead of meaning.
        palette = colors or [self.theme.danger]
        animations = []
        for index, nodes in enumerate(self.get_duplicate_groups().values()):
            color = palette[index % len(palette)]
            for node in nodes:
                # Transform the complete node. Animating only the circle while
                # its label remains nested in the tree can make Manim detach
                # and reinsert the siblings on different frames.
                target = node["mobject"].copy()
                target[0].set_color(color).set_fill(color, opacity=opacity)
                animations.append(Transform(node["mobject"], target))
        return AnimationGroup(*animations, lag_ratio=0.04)

    def show_cache_hit(self, node_data, color=None):
        """Mark a repeated node as a lookup rather than a recomputation."""
        color = color or self.theme.accent
        badge = Text("cache hit", font_size=16, color=color)
        badge.next_to(node_data["mobject"], RIGHT, buff=0.10)
        node_data["cache_badge"] = badge
        # Keep the badge owned by the tree so clearing or replacing the tree
        # cannot leave an orphaned label in later scenes.
        self.add(badge)
        return AnimationGroup(Indicate(node_data["mobject"], color=color),
                              FadeIn(badge, shift=LEFT * 0.08))

    def build_state_graph(self, direction=DOWN, node_buff=0.28, edge_color=None):
        """Return a DAG containing one node for each unique recursive state."""
        edge_color = edge_color or self.theme.muted
        grouped = self.get_duplicate_groups(include_singletons=True)
        canonical = {key: nodes[0] for key, nodes in grouped.items()}
        depths = {}
        for node_data, depth in self.iter_nodes():
            key = self.state_key(node_data["args"])
            depths[key] = min(depths.get(key, depth), depth)

        graph = VGroup()
        graph.nodes = {}
        graph.edges = VGroup()
        levels = {}
        for key in canonical:
            levels.setdefault(depths[key], []).append(key)
        for depth, keys in sorted(levels.items()):
            row = VGroup()
            for key in keys:
                node = canonical[key]["mobject"].copy()
                graph.nodes[key] = node
                row.add(node)
            row.arrange(RIGHT, buff=node_buff)
            row.move_to(DOWN * depth * 0.9)
            graph.add(row)

        seen_edges = set()
        for node_data, _depth in self.iter_nodes():
            parent_key = self.state_key(node_data["args"])
            for child in node_data["children"]:
                child_key = self.state_key(child["args"])
                pair = (parent_key, child_key)
                if pair in seen_edges:
                    continue
                seen_edges.add(pair)
                parent = graph.nodes[parent_key]
                target = graph.nodes[child_key]
                delta = target.get_center() - parent.get_center()
                edge = Arrow(
                    parent[0].get_boundary_point(delta),
                    target[0].get_boundary_point(-delta),
                    buff=0.02, color=edge_color, stroke_width=2,
                    max_tip_length_to_length_ratio=0.12,
                )
                graph.edges.add(edge)
        graph.add_to_back(graph.edges)
        graph.move_to(self)
        return graph

    def collapse_to_state_graph(self, **kwargs):
        """Replace this tree with its unique-state DAG."""
        self.memoized_graph = self.build_state_graph(**kwargs)
        return ReplacementTransform(self, self.memoized_graph)

    def get_layer_annotations(
        self,
        depths=None,
        label_fn=None,
        side=LEFT,
        buff=0.35,
        guide_buff=0.08,
        guide_color=None,
        guide_opacity=0.5,
        guide_dash_length=0.08,
    ):
        """Build labels and dashed guides aligned to selected tree layers.

        ``label_fn`` receives ``(depth, nodes_at_depth)`` and returns any
        Mobject.  The result is a VGroup with public ``labels`` and ``guides``
        attributes so scenes can animate them together or independently.
        """
        layers = self.get_layers()
        selected = list(range(len(layers))) if depths is None else list(depths)
        labels = VGroup()
        guides = VGroup()
        left_side = side[0] < 0

        for depth in selected:
            if depth < 0 or depth >= len(layers):
                continue
            nodes = layers[depth]
            label = (
                label_fn(depth, nodes)
                if label_fn is not None
                else Text(
                    f"layer {depth}", font_size=18, color=self.theme.muted,
                )
            )
            y = sum(node["mobject"].get_y() for node in nodes) / len(nodes)
            label.next_to(self, LEFT if left_side else RIGHT, buff=buff).set_y(y)
            anchor = min(nodes, key=lambda n: n["mobject"].get_x()) if left_side else max(
                nodes, key=lambda n: n["mobject"].get_x()
            )
            label_point = label.get_right() if left_side else label.get_left()
            node_point = anchor["shape"].get_left() if left_side else anchor["shape"].get_right()
            direction = RIGHT if left_side else LEFT
            guide = DashedLine(
                label_point + direction * guide_buff,
                node_point - direction * guide_buff,
                color=guide_color or self.theme.muted,
                stroke_width=1.2,
                stroke_opacity=guide_opacity,
                dash_length=guide_dash_length,
            )
            labels.add(label)
            guides.add(guide)

        annotations = VGroup(guides, labels)
        annotations.labels = labels
        annotations.guides = guides
        return annotations

    def get_set_state_anim(self, node_data, state):
        """Returns an animation to change a node's state"""
        node_data["state"] = state
        target = node_data["mobject"].copy()
        if state == NodeState.ACTIVE:
            target[0].set_color(self.theme.accent).set_stroke(width=4)
        elif state == NodeState.RESOLVED:
            target[0].set_color(self.theme.success).set_fill(
                self.theme.success, opacity=0.3,
            )
        else:
            target[0].set_color(self.theme.node).set_stroke(width=2)
        return Transform(node_data["mobject"], target)

    def get_unroll_anim(self, lag_ratio=0.5):
        """Grow edges and reveal nodes in a smooth top-to-bottom wave.

        This is implemented as one animation rather than nested ``FadeIn``
        instances.  Consequently Manim cannot pre-add labels from a future
        branch and briefly expose them before that branch begins.
        """
        node_records = []
        edge_records = []
        max_depth = 0
        for node_data, depth in self.iter_nodes():
            max_depth = max(max_depth, depth)
            node_records.append((node_data["mobject"], node_data["mobject"].copy(), depth))
            for edge in node_data["edges"]:
                # Outgoing edges visually belong to the children they reveal.
                edge_records.append((edge, edge.copy(), depth + 1))

        for node, _original, _depth in node_records:
            node.set_opacity(0)
        for edge, original, _depth in edge_records:
            edge.pointwise_become_partial(original, 0, 0)

        # Values below one stagger levels; each level itself still gets enough
        # time to ease in instead of popping on a single frame.
        level_duration = 1.35
        level_step = max(0.34, min(0.82, float(lag_ratio) * 3.0 + 0.34))
        total = max_depth * level_step + level_duration

        def level_alpha(alpha, depth):
            elapsed = alpha * total - depth * level_step
            return smooth(max(0.0, min(1.0, elapsed / level_duration)))

        def reveal(_tree, alpha):
            for node, original, depth in node_records:
                amount = level_alpha(alpha, depth)
                node.become(
                    original.copy()
                    .scale(0.82 + 0.18 * amount, about_point=original.get_center())
                    .set_opacity(amount)
                )
            for edge, original, depth in edge_records:
                amount = level_alpha(alpha, depth)
                edge.pointwise_become_partial(original, 0, amount)
                edge.set_opacity(amount)

        return UpdateFromAlphaFunc(self, reveal)

    def prepare_layered_unroll(self):
        """Hide a tree once so selected depth ranges can be revealed later.

        This supports narration-driven scenes where the root, its first
        children, and the remaining tree are introduced by separate phrases.
        Pristine copies keep future labels and edges from flashing early.
        """
        if not hasattr(self, "_layered_unroll_nodes"):
            self._layered_unroll_nodes = [
                (node_data["mobject"], node_data["mobject"].copy(), depth)
                for node_data, depth in self.iter_nodes()
            ]
            self._layered_unroll_edges = []
            for node_data, depth in self.iter_nodes():
                for edge in node_data["edges"]:
                    self._layered_unroll_edges.append((edge, edge.copy(), depth + 1))
            for node, _original, _depth in self._layered_unroll_nodes:
                node.set_opacity(0)
            for edge, original, _depth in self._layered_unroll_edges:
                edge.pointwise_become_partial(original, 0, 0)
                edge.set_opacity(0)
        return self

    def get_depth_reveal_anim(self, start_depth, end_depth=None, lag_ratio=0.05):
        """Reveal an inclusive range of prepared tree depths smoothly."""
        self.prepare_layered_unroll()
        end_depth = start_depth if end_depth is None else end_depth
        nodes = [record for record in self._layered_unroll_nodes
                 if start_depth <= record[2] <= end_depth]
        edges = [record for record in self._layered_unroll_edges
                 if start_depth <= record[2] <= end_depth]
        if not nodes and not edges:
            return Wait(0.01)

        span = max(0, end_depth - start_depth)
        level_duration = 1.0
        level_step = max(0.18, min(0.55, float(lag_ratio) * 3.0 + 0.18))
        total = span * level_step + level_duration

        def level_alpha(alpha, depth):
            elapsed = alpha * total - (depth - start_depth) * level_step
            return smooth(max(0.0, min(1.0, elapsed / level_duration)))

        def reveal(_tree, alpha):
            for node, original, depth in nodes:
                amount = level_alpha(alpha, depth)
                node.become(
                    original.copy()
                    .scale(0.84 + 0.16 * amount, about_point=original.get_center())
                    .set_opacity(amount)
                )
            for edge, original, depth in edges:
                amount = level_alpha(alpha, depth)
                edge.pointwise_become_partial(original, 0, amount)
                edge.set_opacity(amount)

        return UpdateFromAlphaFunc(self, reveal)

    def get_fade_in_anim(self):
        """Safely fade in a complete tree without a one-frame label flash.

        Opacity is driven on the actual drawable family members.  Animating
        opacity only on the outer ``VGroup`` lets circles and MathTex glyphs
        initialize at different moments in some renderers.
        """
        members = list(self.family_members_with_points())
        styles = [
            (member, member.get_fill_opacity(), member.get_stroke_opacity())
            for member in members
        ]
        for member, _fill, _stroke in styles:
            member.set_fill(opacity=0)
            member.set_stroke(opacity=0)

        def reveal(_tree, alpha):
            amount = smooth(alpha)
            for member, fill_opacity, stroke_opacity in styles:
                member.set_fill(opacity=fill_opacity * amount)
                member.set_stroke(opacity=stroke_opacity * amount)

        return UpdateFromAlphaFunc(self, reveal)
