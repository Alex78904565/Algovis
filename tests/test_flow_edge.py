import unittest

import numpy as np
from manim import ORIGIN, RIGHT, UP, interpolate_color

from algovis import FlowEdge, highlight_edges
from algovis.core.flow import DEFAULT_FLOW_GLOW


class FlowEdgeTest(unittest.TestCase):
    def test_width_uses_capacity_color_uses_fraction_and_speed_uses_flow(self):
        small = FlowEdge(ORIGIN, 4 * RIGHT, 4)
        large = FlowEdge(ORIGIN, 4 * RIGHT, 16)
        self.assertAlmostEqual(large.track.height / small.track.height, 2.)
        self.assertAlmostEqual(small.arrows[0].height, small.track.height)
        self.assertEqual(small.arrows[0].get_fill_opacity(), 0.)

        origin = small.arrows[0].get_center().copy()
        small.update(.1)
        np.testing.assert_allclose(small.arrows[0].get_center(), origin)
        small.set_flow(2)
        large.set_flow(2)
        low_opacity = small.arrows[0].get_fill_opacity()
        self.assertGreater(low_opacity, 0.)
        self.assertAlmostEqual(large.arrows[0].get_fill_opacity(), low_opacity)
        np.testing.assert_allclose(small.arrows[0].get_center(), origin)
        small.update(.1)
        large.update(.1)
        self.assertAlmostEqual(small.arrows[0].get_x() - origin[0], .1 * .19 * 2)
        self.assertAlmostEqual(small.arrows[0].get_x(), large.arrows[0].get_x())
        empty, full = small.utilization_colors
        np.testing.assert_allclose(empty.to_rgb(), .48 * full.to_rgb())
        midpoint = interpolate_color(empty, full, .5)
        self.assertEqual(small.track.get_fill_color().to_hex(), midpoint.to_hex())
        small.set_flow(4)
        self.assertEqual(small.track.get_fill_color().to_hex(), "#4387E4")
        self.assertAlmostEqual(small.arrows[0].get_fill_opacity(), 2 * low_opacity)
        self.assertEqual(small.glow[0].get_fill_opacity(), 0.)

    def test_copied_belt_keeps_chevrons_within_its_moved_mouths(self):
        edge = FlowEdge(ORIGIN, 2.8 * RIGHT, 9, flow=9)
        placed = edge.copy().rotate(np.pi / 2, about_point=ORIGIN).shift(UP)
        original = edge.arrows[0].get_center().copy()
        for _ in range(40):
            placed.update(1 / 30)
            for chevron in placed.arrows:
                self.assertGreaterEqual(chevron.get_bottom()[1], 1 - 1e-9)
                self.assertLessEqual(chevron.get_top()[1], 3.8 + 1e-9)
        np.testing.assert_allclose(edge.arrows[0].get_center(), original)

    def test_sweep_follows_speed(self):
        edge = FlowEdge(ORIGIN, 4 * RIGHT, 14, flow=4)
        arrow = edge.arrows[0]
        initial_center = arrow.get_center().copy()
        initial_sweep = arrow.width
        edge.set_flow(13)
        self.assertGreater(arrow.width, initial_sweep)
        np.testing.assert_allclose(arrow.get_center(), initial_center)
        self.assertGreater(arrow.get_fill_color().to_rgb()[1], edge.track.get_fill_color().to_rgb()[1])

    def test_eased_flow_changes_keep_a_split_balanced_while_belts_move(self):
        inlet = FlowEdge(ORIGIN, 4 * RIGHT, 14, flow=6)
        upper = FlowEdge(ORIGIN, 4 * RIGHT, 9, flow=4)
        effects = inlet.animate_flow(11), upper.animate_flow(9)
        self.assertEqual(inlet.flow, 6)
        for effect in effects:
            effect.begin()
        start = inlet.arrows[0].get_x()
        for alpha in (.25, .5, .75):
            for effect in effects:
                effect.interpolate(alpha)
            self.assertAlmostEqual(inlet.flow, upper.flow + 2)
            if alpha == .25:
                self.assertLess(inlet.flow, 6 + .25 * 5)
                inlet.update(.1)
                self.assertGreater(inlet.arrows[0].get_x(), start)
        for effect in effects:
            effect.finish()
        self.assertEqual((inlet.flow, upper.flow), (11, 9))

    def test_predicate_replaces_glow_selection_while_belts_run(self):
        inlet, upper, lower = (FlowEdge(ORIGIN, 4 * RIGHT, 4, flow=flow)
                               for flow in (3, 4, 2))
        edges = inlet, upper, lower
        path = {inlet, lower}
        track_color = inlet.track.get_fill_color()
        start = inlet.arrows[0].get_x()
        for effect in highlight_edges(edges, path.__contains__, color="#6EE7FF"):
            effect.begin()
            effect.interpolate(.5)
            self.assertFalse(effect.mobject.updating_suspended)
            effect.mobject.update(.1)
            effect.finish()

        self.assertGreater(inlet.arrows[0].get_x(), start)
        self.assertEqual(inlet.track.get_fill_color(), track_color)
        self.assertEqual(inlet.glow[0].get_fill_color().to_hex(), "#6EE7FF")
        self.assertGreater(inlet.glow[0].get_fill_opacity(), 0.)
        self.assertEqual(upper.glow[0].get_fill_opacity(), 0.)

        lower.set_flow(4)
        for effect in highlight_edges(edges, lambda edge: edge.flow == edge.capacity):
            effect.begin()
            effect.finish()
        self.assertEqual(inlet.glow[0].get_fill_opacity(), 0.)
        self.assertGreater(upper.glow[0].get_fill_opacity(), 0.)
        self.assertGreater(lower.glow[0].get_fill_opacity(), 0.)
        self.assertEqual(upper.glow[0].get_fill_color().to_hex(), DEFAULT_FLOW_GLOW)
        self.assertEqual(lower.glow[0].get_fill_color().to_hex(), DEFAULT_FLOW_GLOW)


if __name__ == "__main__":
    unittest.main()
