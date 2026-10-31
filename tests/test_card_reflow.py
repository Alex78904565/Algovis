import unittest

import numpy as np
from manim import Group, Scene, Square

from algovis import CenteredScene, SlideObject, ViewTransition
from algovis.composition import _axis_reflow, _reflow_intersects
from tests.test_composition import apply, start, finish


class ReflowCards(Group):
    _algovis_layout_container = True
    _algovis_axis_reflow = True

    def __init__(self, *cards):
        self.cards = list(cards)
        super().__init__(*cards)


class CardReflowTests(unittest.TestCase):
    def test_grid_to_row_clears_siblings_before_converging_vertically(self):
        source=[Square(.9).move_to(p) for p in ((0,1,0),(1.2,1,0),(0,-.2,0),(1.2,-.2,0))]
        targets=[s.copy().move_to((i*1.2-1.8,.4,0)) for i,s in enumerate(source)]
        self.assertTrue(_reflow_intersects(source,targets))
        middle=_axis_reflow(source,targets)
        self.assertIsNotNone(middle)
        self.assertFalse(_reflow_intersects(source,middle))
        self.assertFalse(_reflow_intersects(middle,targets))
        for before,mid,after in zip(source,middle,targets):
            self.assertAlmostEqual(before.get_y(),mid.get_y())
            self.assertAlmostEqual(after.get_x(),mid.get_x())

    def test_compiler_coordinates_the_reflow_and_keeps_card_identities(self):
        cards=[Square(.9).move_to(p) for p in ((0,1,0),(1.2,1,0),(0,-.2,0),(1.2,-.2,0))]
        first=CenteredScene();first.add('items',ReflowCards(*cards))
        second=first.fork()
        targets=second.target('items')
        for i,card in enumerate(targets):card.move_to((i*1.2-1.8,.4,0))
        identities=[id(c) for c in cards]
        scene=Scene();first.install(scene)
        plan=ViewTransition(first,second)
        self.assertTrue(plan._reflow_groups)
        for animation in plan.animations(scene):
            start(animation,scene)
            for alpha in np.linspace(0,1,31):
                animation.interpolate(alpha)
                self.assertFalse(_reflow_intersects(cards,cards))
            finish(animation,scene)
        plan.commit(scene)
        self.assertEqual(identities,[id(c) for c in cards])
        for card,target in zip(cards,targets):
            np.testing.assert_allclose(card.get_center(),target.get_center())

    def test_clear_translation_keeps_the_original_single_phase(self):
        cards=[Square(.9).move_to((i*1.2,0,0)) for i in range(4)]
        self.assertIsNone(_axis_reflow(cards,[c.copy().shift((0,1,0)) for c in cards]))


if __name__ == '__main__':
    unittest.main()
