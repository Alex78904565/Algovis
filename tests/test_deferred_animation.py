import unittest

from manim import AnimationGroup, Create, FadeOut, Line, Scene, Square, Succession, Transform, Wait, RIGHT

from algovis import ApplyDefinition, DeferredAnimation, ReplaceContent


class DeferredAnimationTests(unittest.TestCase):
    def test_definition_copy_is_adopted_before_the_next_substitution_begins(self):
        scene=Scene()
        definition,result=Square(),Square().shift(2*RIGHT)
        scene.add(definition)
        transfer=ApplyDefinition(definition,None,result)
        first=DeferredAnimation(lambda:AnimationGroup(transfer,Create(Line())),run_time=1)
        next_phase=[]
        def substitute():
            family=scene.get_mobject_family_members()
            next_phase.append((result in family,transfer.traveller in family))
            return Transform(result,result.copy().shift(RIGHT))
        sequence=Succession(first,DeferredAnimation(substitute,run_time=1),Wait(run_time=1))
        scene.add_mobjects_from_animations([sequence]);sequence._setup_scene(scene);sequence.begin()
        sequence.interpolate(.4)
        self.assertEqual(next_phase,[(True,False)])
        sequence.finish();sequence.clean_up_from_scene(scene)
        self.assertIn(result,scene.get_mobject_family_members())
        self.assertNotIn(transfer.traveller,scene.get_mobject_family_members())
        self.assertAlmostEqual(result.get_x(),3)

    def test_substitution_and_cancellation_wait_for_their_own_phase(self):
        scene = Scene()
        general, expanded, result = Square(), Square().shift(RIGHT), Square().shift(2 * RIGHT)
        strike = Line(expanded.get_corner([-1, -1, 0]), expanded.get_corner([1, 1, 0]))
        sequence = Succession(
            Create(general, run_time=1), Wait(run_time=1),
            DeferredAnimation(lambda: ReplaceContent(general, expanded), run_time=1),
            DeferredAnimation(lambda: Create(strike), run_time=1),
            DeferredAnimation(lambda: AnimationGroup(ReplaceContent(expanded, result), FadeOut(strike)), run_time=1),
        )
        scene.add_mobjects_from_animations([sequence])
        sequence._setup_scene(scene)
        sequence.begin()
        for alpha in (0, .1, .2, .3, .39):
            sequence.interpolate(alpha)
            family = scene.get_mobject_family_members()
            self.assertNotIn(expanded, family)
            self.assertNotIn(strike, family)
            self.assertNotIn(result, family)
        sequence.interpolate(.59)
        family = scene.get_mobject_family_members()
        self.assertIn(expanded, family)
        self.assertNotIn(strike, family)
        self.assertNotIn(result, family)
        sequence.interpolate(.79)
        self.assertIn(strike, scene.get_mobject_family_members())
        self.assertNotIn(result, scene.get_mobject_family_members())
        sequence.finish()
        sequence.clean_up_from_scene(scene)
        family = scene.get_mobject_family_members()
        self.assertIn(result, family)
        for old in (general, expanded, strike):
            self.assertNotIn(old, family)

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
