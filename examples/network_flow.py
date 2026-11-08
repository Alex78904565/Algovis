"""Silent 10-second preview of the shared FlowEdge component.

Render with: python -m manim -qm examples/network_flow.py NetworkFlowExample
"""
import numpy as np
from manim import Circle, DOWN, LEFT, RIGHT, UP, Rectangle, UpdateFromAlphaFunc, VGroup

from algovis import FlowEdge, LessonStyle, Move, Retire, Reveal, ViewScene, highlight_edges
from algovis.core.flow import DEFAULT_FLOW_GLOW


class _Vertex(VGroup):
    def __init__(self, name, point, style):
        disk = Circle(radius=.37, color=style.theme.muted, stroke_width=1.8,
                      fill_color=style.theme.surface, fill_opacity=1)
        label = style.text(name, type_role="body").move_to(disk)
        super().__init__(disk, label)
        self.move_to(point).set_z_index(1)


class NetworkFlowExample(ViewScene):
    def construct(self):
        style = LessonStyle(theme=self.theme)
        inlet_start = np.array([-2.2, .05, 0])
        inlet_end = np.array([2.2, .05, 0])
        to_left = 3.05 * LEFT
        split = inlet_end + to_left
        upper_end = np.array([4.9, 1.52, 0])
        lower_end = np.array([4.9, -1.42, 0])

        # The inlet reaches 13/14 while the two branches are full.
        inlet = FlowEdge(inlet_start, inlet_end, 14)
        # Separate the mouths inside v so the two belts leave its rim cleanly.
        upper = FlowEdge(split + .14 * UP, upper_end, 9, flow=4)
        lower = FlowEdge(split + .14 * DOWN, lower_end, 4, flow=2)
        source = _Vertex("s", inlet_start, style)
        junction = _Vertex("v", inlet_end, style)
        sinks = [_Vertex(name, point, style) for name, point in
                 (("a", upper_end), ("b", lower_end))]

        header = VGroup(style.text("NETWORK FLOW", type_role="note", role="current"),
                        style.text("Reading a flow edge", type_role="display"))
        header.arrange(DOWN, buff=.16).move_to([0, 2.95, 0])
        legend = self._legend(style, inlet.utilization_colors).move_to([0, -3.05, 0])
        inlet_label = self._readout(style, inlet)
        self.mount_view(header, legend, inlet, source, junction, inlet_label)
        self.wait(.9)

        self._ease_flows(style, (inlet,), (1,), (inlet_label,), run_time=.4)
        self.wait(.8)
        self._ease_flows(style, (inlet,), (6,), (inlet_label,), run_time=.5)

        # Shift the same moving belt to the left to open room for the fork.
        self.animate_view(*(Move(item, item.copy().shift(to_left),
                                 suspend_mobject_updating=False)
                            for item in (inlet, source, junction, inlet_label)), run_time=.6)
        heading = style.text("Flow in = flow out", type_role="label", role="muted")
        heading.move_to(split + 1.20 * DOWN)
        labels = (inlet_label, self._readout(style, upper),
                  self._readout(style, lower, side=DOWN),
                  self._balance(style, split, upper, lower))
        self.animate_view(*(Reveal(item, suspend_mobject_updating=False)
                            for item in (upper, lower, *sinks, heading, *labels[1:])), run_time=.6)
        self.wait(1.4)

        edges = inlet, upper, lower
        self._ease_flows(style, edges, (11, 9, 2), labels, run_time=.6)
        path = style.text("Path s → v → b", type_role="label").set_color(DEFAULT_FLOW_GLOW)
        path.move_to([2.7, -2.23, 0])
        path_edges = {inlet, lower}
        self.animate_view(Reveal(path),
                          *highlight_edges(edges, path_edges.__contains__),
                          run_time=.2)
        self.wait(1.1)

        self._ease_flows(style, edges, (13, 9, 4), labels, run_time=.4)
        self.animate_view(Retire(path), *highlight_edges(edges, lambda edge: False), run_time=.2)
        full_pipes = style.text("Full pipes", type_role="label").set_color(DEFAULT_FLOW_GLOW)
        full_pipes.move_to(path)
        selected = highlight_edges(edges, lambda edge: edge.flow == edge.capacity)
        self.animate_view(Reveal(full_pipes), *selected, run_time=.2)
        self.wait(2.1)

    def _ease_flows(self, style, edges, targets, labels, *, run_time):
        # Only the settled integer states are displayed. The pipe artwork eases
        # between them, and every readout switches on the same finishing frame.
        def settle_label(label, text):
            def update(mob, alpha):
                if alpha == 1 and mob.text != text:
                    mob.become(style.text(text, type_role="equation").move_to(mob))
                    mob.text = text

            return UpdateFromAlphaFunc(label, update)

        flows = []
        readouts = []
        for edge, target, label in zip(edges, targets, labels):
            if edge.flow != target:
                flows.append(edge.animate_flow(target))
                readouts.append(settle_label(label, f"{target:g}/{edge.capacity:g}"))
        if len(edges) == 3:
            incoming, top, bottom = targets
            readouts.append(settle_label(labels[-1], f"{incoming:g} = {top:g} + {bottom:g}"))
        self.animate_view(*flows, *readouts, run_time=run_time)

    @staticmethod
    def _readout(style, edge, *, side=UP):
        value = style.text(f"{round(edge.flow)}/{edge.capacity:g}", type_role="equation")
        return value.move_to(edge.track.get_center() + .65 * side)

    @staticmethod
    def _balance(style, split, upper, lower):
        top, bottom = round(upper.flow), round(lower.flow)
        equation = style.text(f"{top + bottom} = {top} + {bottom}", type_role="equation")
        return equation.move_to(split + 1.73 * DOWN)

    @staticmethod
    def _legend(style, utilization_colors):
        width = style.text("Width  ∝  √capacity", type_role="body")
        speed = style.text("Arrow speed  ∝  flow", type_role="body")
        ramp = Rectangle(width=1.87, height=.12, stroke_width=0, fill_opacity=1,
                         fill_color=list(utilization_colors), sheen_direction=RIGHT)
        scale = VGroup(style.text("0%", type_role="note"), ramp,
                       style.text("100%", type_role="note")).arrange(RIGHT, buff=.12)
        utilization = VGroup(style.text("Flow / capacity", type_role="body"), scale)
        utilization.arrange(DOWN, buff=.14)
        return VGroup(width, speed, utilization).arrange(RIGHT, aligned_edge=UP, buff=.80)
