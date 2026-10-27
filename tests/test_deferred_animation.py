import unittest

from manim import AnimationGroup, Create, Scene, Square, Succession, Transform, Wait, RIGHT

from algovis import DeferredAnimation


class DeferredAnimationTests(unittest.TestCase):
    def test_future_guide_stays_absent_until_both_base_steps_finish(self):
        scene = Scene()
        guide = Square()
        created = []

        def reveal():
            created.append(True)
            return AnimationGroup(Create(guide), run_time=1)

        deferred = DeferredAnimation(reveal, run_time=1)
        sequence = Succession(Wait(run_time=1), Wait(run_time=1), deferred)
        scene.add_mobjects_from_animations([sequence])
        sequence._setup_scene(scene)
        sequence.begin()
        for alpha in (0, .2, .4, .6):
            sequence.interpolate(alpha)
            self.assertNotIn(guide, scene.get_mobject_family_members())
            self.assertEqual(created, [])
        sequence.interpolate(.7)
        self.assertIn(guide, scene.get_mobject_family_members())
        self.assertEqual(created, [True])
        sequence.finish()
        sequence.clean_up_from_scene(scene)
        self.assertIn(guide, scene.get_mobject_family_members())

    def test_factory_uses_geometry_after_preceding_move(self):
        scene = Scene()
        source, guide = Square(), Square()
        scene.add(source)
        captured = []

        def reveal():
            guide.move_to(source)
            captured.append(guide.get_x())
            return Create(guide)

        deferred = DeferredAnimation(reveal, run_time=1)
        sequence = Succession(Transform(source, source.copy().shift(3 * RIGHT), run_time=1), deferred)
        scene.add_mobjects_from_animations([sequence])
        sequence._setup_scene(scene)
        sequence.begin()
        sequence.interpolate(.5)
        self.assertAlmostEqual(captured[0], 3)
        sequence.finish()
        sequence.clean_up_from_scene(scene)


if __name__ == '__main__':
    unittest.main()
