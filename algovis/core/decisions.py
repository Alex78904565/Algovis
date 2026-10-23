from manim import *


class DecisionFanout(VGroup):
    """Visualize legal choices leaving a state and merging through min/max."""

    def __init__(self, state, choices, optimizer="min", direction=DOWN,
                 choice_buff=0.55, branch_color=GREY_B, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self.choice_specs = choices
        self.choice_nodes = VGroup()
        self.branches = VGroup()
        self.choice_labels = VGroup()
        self.disabled = set()

        for index, spec in enumerate(choices):
            if isinstance(spec, dict):
                target = spec.get("target")
                label_value = spec.get("label", str(index))
                enabled = spec.get("enabled", True)
            else:
                label_value, target = spec
                enabled = True
            target = target if isinstance(target, Mobject) else self._default_node(target)
            self.choice_nodes.add(target)
            if not enabled:
                self.disabled.add(index)
        self.choice_nodes.arrange(RIGHT, buff=choice_buff)
        self.choice_nodes.next_to(state, direction, buff=0.9)

        for index, spec in enumerate(choices):
            label_value = spec.get("label", str(index)) if isinstance(spec, dict) else spec[0]
            edge = Arrow(state.get_bottom(), self.choice_nodes[index].get_top(), buff=0.06,
                         color=branch_color, stroke_width=2,
                         max_tip_length_to_length_ratio=0.12)
            label = label_value if isinstance(label_value, Mobject) else Text(str(label_value), font_size=18)
            # Keeping labels near their destination prevents variable-choice
            # captions from bunching together at the shared parent node.
            label.next_to(self.choice_nodes[index], UP, buff=0.06)
            label.add_background_rectangle(color=BLACK, opacity=0.85, buff=0.03)
            self.branches.add(edge)
            self.choice_labels.add(label)

        self.gate = VGroup(
            Circle(radius=0.28, color=YELLOW),
            MathTex(r"\min" if optimizer == "min" else r"\max").scale(0.42),
        ).next_to(self.choice_nodes, DOWN, buff=0.55)
        self.merge_edges = VGroup(*[
            Arrow(node.get_bottom(), self.gate.get_top(), buff=0.05,
                  color=branch_color, stroke_width=1.7,
                  max_tip_length_to_length_ratio=0.10)
            for node in self.choice_nodes
        ])
        self.add(state, self.branches, self.choice_labels, self.choice_nodes,
                 self.merge_edges, self.gate)
        for index in self.disabled:
            self.choice_nodes[index].set_opacity(0.3)
            self.branches[index].set_opacity(0.2)
            self.choice_labels[index].set_opacity(0.3)

    @staticmethod
    def _default_node(value):
        label = MathTex(str(value)).scale(0.55)
        box = RoundedRectangle(corner_radius=0.08, width=max(1.0, label.width + 0.3),
                               height=0.55, color=BLUE_B)
        return VGroup(box, label)

    def grow(self, show_state=True):
        stages = []
        if show_state:
            stages.append(FadeIn(self.state))
        stages.extend([
            LaggedStart(*[AnimationGroup(GrowArrow(edge), FadeIn(label), FadeIn(node))
                          for edge, label, node in zip(self.branches, self.choice_labels, self.choice_nodes)],
                        lag_ratio=0.12),
            AnimationGroup(Create(self.merge_edges), FadeIn(self.gate)),
        ])
        return Succession(*stages)

    def set_choice_enabled(self, index, enabled=True):
        opacity = 1.0 if enabled else 0.25
        if enabled:
            self.disabled.discard(index)
        else:
            self.disabled.add(index)
        return AnimationGroup(
            self.choice_nodes[index].animate.set_opacity(opacity),
            self.branches[index].animate.set_opacity(opacity),
            self.choice_labels[index].animate.set_opacity(opacity),
        )

    def choose(self, index, color=GREEN_B):
        return AnimationGroup(
            Indicate(self.choice_nodes[index], color=color),
            self.branches[index].animate.set_color(color).set_stroke(width=4),
            self.merge_edges[index].animate.set_color(color).set_stroke(width=4),
        )
