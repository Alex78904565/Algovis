"""A straight directed belt for visualizing a capacitated flow."""
from math import atan2, ceil, isfinite, sqrt

import numpy as np
from manim import (
    Line, ManimColor, Polygon, RoundedRectangle, UpdateFromAlphaFunc, VGroup, VMobject,
    interpolate, interpolate_color, smooth,
)


DEFAULT_FLOW_GLOW = "#FFFFFF"


class FlowEdge(VGroup):
    """Capacity sets width, flow sets speed and contrast, and utilization sets fill color.

    Endpoints are 3D scene coordinates in the same XY plane. Use the same width
    and speed factors, arrow spacing, and contrast reference across a diagram.
    ``arrow_contrast_flow`` is the flow at which the chevrons reach peak opacity.
    By default, utilization changes the value of ``full_color`` at fixed hue and saturation.
    Use ``highlight_edges`` to apply a glow to a chosen set of pipes.
    Use ``animate_flow`` for an eased transition that keeps the belt's phase.
    """

    def __init__(self, start, end, capacity, *, flow=0, width_factor=.12,
                 speed_factor=.19, arrow_spacing=.48, empty_color=None,
                 full_color="#4387E4", arrow_color=None, arrow_contrast_flow=14):
        super().__init__()
        if not all(isfinite(value) and value > 0
                   for value in (capacity, width_factor, speed_factor, arrow_spacing,
                                 arrow_contrast_flow)):
            raise ValueError("Capacity and belt settings must be positive and finite")
        start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
        if start.shape != (3,) or end.shape != (3,):
            raise ValueError("A flow edge needs two 3D scene coordinates")
        delta = end - start
        self._length = float(np.linalg.norm(delta))
        if not isfinite(self._length) or self._length == 0 or delta[2] != 0:
            raise ValueError("A flow edge needs distinct, finite endpoints in one XY plane")

        self.capacity = capacity
        width = width_factor * sqrt(capacity)
        normal = np.array([-delta[1], delta[0], 0]) * (width / (2 * self._length))
        self.track = Polygon(start - normal, end - normal, end + normal, start + normal,
                             stroke_width=0, fill_opacity=1)
        self._selection_color = ManimColor(DEFAULT_FLOW_GLOW)
        self._selection_amount = 0.
        self.glow = self._make_glow(width, (start + end) / 2, atan2(delta[1], delta[0]))
        self._glow_wash = self.track.copy().set_fill(opacity=0)
        self._axis = Line(start, end, stroke_width=0)
        full = ManimColor(full_color)
        empty = ManimColor(full.to_rgb() * .48 if empty_color is None else empty_color)
        self.utilization_colors = empty, full
        self._arrow_contrast_flow = arrow_contrast_flow
        self._spacing = arrow_spacing
        self._speed_factor = speed_factor
        self._phase = min(self._length, arrow_spacing) / 2
        # The sweep and thickness together always leave a gap between marks.
        self._max_sweep = min(.26, arrow_spacing * .55, self._length / 4)
        self._arrow_thickness = min(.14, width * .56, arrow_spacing * .30, self._length / 4)
        self._arrow_height = width / 2
        chevron_color = "#FFFFFF" if arrow_color is None else arrow_color
        self.arrows = VGroup(*(VMobject(stroke_width=0, fill_color=chevron_color)
                               for _ in range(ceil(self._length / arrow_spacing))))
        self.add(self.glow, self.track, self._glow_wash, self._axis, self.arrows)
        self.set_flow(flow)
        self.add_updater(self._update_belt)

    @property
    def utilization(self):
        return self.flow / self.capacity

    @property
    def speed(self):
        return self._speed_factor * self.flow

    def _validate_flow(self, flow):
        if not isfinite(flow) or not 0 <= flow <= self.capacity:
            raise ValueError("Flow must be finite and between zero and capacity")

    def set_flow(self, flow):
        self._validate_flow(flow)
        self.flow = flow
        fill = interpolate_color(*self.utilization_colors, self.utilization)
        self.track.set_fill(fill)
        self.arrows.set_fill(opacity=.60 * min(flow / self._arrow_contrast_flow, 1.))
        self._set_chevron_profile()
        self._update_belt(self, 0)
        return self

    def animate_flow(self, flow, *, run_time=.6):
        """Ease to a feasible flow, keeping the belt in motion."""
        self._validate_flow(flow)
        initial = None

        def update(edge, alpha):
            nonlocal initial
            if initial is None or alpha == 0:
                initial = edge.flow
            edge.set_flow(interpolate(initial, flow, alpha))

        return UpdateFromAlphaFunc(self, update, rate_func=smooth, run_time=run_time,
                                   suspend_mobject_updating=False)

    def highlight(self, active=True, *, color=None, run_time=.25):
        """Fade this edge's selection glow while its belt continues to run."""
        if active and color is None:
            color = DEFAULT_FLOW_GLOW
        target_color = ManimColor(color) if color is not None else None
        target_amount = float(bool(active))
        starting_paint = None

        def update(edge, alpha):
            nonlocal starting_paint
            if starting_paint is None or alpha == 0:
                starting_paint = edge._selection_color, edge._selection_amount
            initial_color, initial_amount = starting_paint
            edge._selection_color = interpolate_color(
                initial_color, target_color or initial_color, alpha,
            )
            edge._selection_amount = initial_amount + (target_amount - initial_amount) * alpha
            edge._paint_glow()

        return UpdateFromAlphaFunc(self, update, run_time=run_time, suspend_mobject_updating=False)

    def _make_glow(self, width, center, angle):
        # Nested fills approximate a Gaussian falloff along the pipe's sides.
        spreads = np.linspace(.27, .014, 20)
        levels = .48 * np.exp(-.5 * (spreads / .105) ** 2)
        previous = np.r_[0., levels[:-1]]
        self._glow_opacities = (levels - previous) / (1 - previous)
        return VGroup(*(RoundedRectangle(width=self._length + 2 * spread,
                                         height=width + 2 * spread,
                                         corner_radius=spread, stroke_width=0, fill_opacity=0)
                        .rotate(angle).move_to(center) for spread in spreads))

    def _paint_glow(self):
        for layer, opacity in zip(self.glow, self._glow_opacities):
            layer.set_fill(self._selection_color, opacity=opacity * self._selection_amount)
        self._glow_wash.set_fill(self._selection_color, opacity=.16 * self._selection_amount)

    def _set_chevron_profile(self):
        # Sweep the arms back with absolute belt speed. The two cubic halves
        # meet at the leading tip with a common tangent.
        sweep = self._max_sweep * (.16 + .84 * self.speed / (self.speed + 1.05))
        height = self._arrow_height
        thickness = self._arrow_thickness
        front = np.array([
            (0, height), (.34 * sweep, .69 * height), (sweep, .19 * height), (sweep, 0),
            (sweep, 0), (sweep, -.19 * height), (.34 * sweep, -.69 * height), (0, -height),
        ])
        back = front[::-1] - (thickness, 0)
        self._arrow_half_length = (sweep + thickness) / 2
        profile = np.concatenate((front, np.linspace(front[-1], back[0], 4), back,
                                  np.linspace(back[-1], front[0], 4)))
        self._chevron_profile = profile - ((sweep - thickness) / 2, 0)

    def _update_belt(self, _edge, dt):
        self._phase = (self._phase + dt * self.speed) % self._spacing
        start, end = self._axis.get_start_and_end()
        forward = (end - start) / self._length
        across = np.array([-forward[1], forward[0], 0])
        offsets = self._chevron_profile @ np.array([forward, across])
        length, head = self._length, self._arrow_half_length
        for index, arrow in enumerate(self.arrows):
            distance = self._phase + index * self._spacing
            # Shrink through either mouth so a wrapping chevron never jumps
            # across the screen or paints beyond its belt.
            center = min(distance, length)
            scale = min(1., center / head, (length - center) / head)
            arrow.set_points(start + center * forward + scale * offsets)


def highlight_edges(edges, predicate, *, color=None, run_time=.25):
    """Return concurrent glow animations for a new selection over these edges.

    The predicate reads each edge's current state. True selects an edge and
    false clears it. Selected edges glow white by default. Pass the returned
    animations together to the scene.
    """
    return tuple(edge.highlight(predicate(edge), color=color, run_time=run_time)
                 for edge in dict.fromkeys(edges))
