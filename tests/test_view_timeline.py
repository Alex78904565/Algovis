import unittest
import warnings
import numpy as np
from manim import (AnimationGroup, Circle, FadeIn, Group, ImageMobject, LEFT, MathTex,
                   MoveAlongPath, RIGHT, Square, Text, VGroup, Wait, Line)

from algovis import (ApplyDefinition, CanvasSlide, ColumnSlide, CopyInto, Draw,
                     LayoutOverrideWarning, MathRow, Move, ProofSlide, Pulse,
                     Replace, Retire, Reveal, SlideScene, Then, Together,
                     ViewSceneMixin, Later, Stagger)


class TimelineScene(ViewSceneMixin, SlideScene):
    pass


class ViewTimelineTests(unittest.TestCase):
    def setUp(self):
        self.scene = TimelineScene()
        self.scene.setup()
        self.addCleanup(self.scene.tear_down)

    def start(self, *operations, duration=1):
        program = self.scene._view_program(operations, duration)
        self.scene.add_mobjects_from_animations([program])
        program._setup_scene(self.scene)
        program.begin()
        return program

    def finish(self, program):
        program.interpolate(1)
        program.finish()
        program.clean_up_from_scene(self.scene)

    def test_layout_groups_preserve_children_when_they_split_and_regroup(self):
        first, second = Square(.5).shift(LEFT), Circle(.3).shift(RIGHT)
        group = VGroup(first, second)
        self.finish(self.start(Reveal(group)))
        self.assertEqual(self.scene.mobjects, [first, second])
        self.assertEqual(group.submobjects, [first, second])
        target = group.copy().shift(RIGHT)
        self.finish(self.start(Move(group, target)))
        self.assertEqual(self.scene.mobjects, [first, second])
        self.assertAlmostEqual(first.get_x(), 0)
        self.assertAlmostEqual(second.get_x(), 2)
        reordered = VGroup(second, first)
        self.scene.mount_view(reordered)
        self.assertCountEqual(self.scene.mobjects, [first, second])

    def test_partial_reveal_does_not_introduce_the_rest_of_a_future_equation(self):
        row = MathRow({'call':'f(', 'index':'i', 'close':')'})
        self.finish(self.start(Reveal(row.part('call'))))
        members = self.scene.get_mobject_family_members()
        self.assertIn(row.part('call'), members)
        self.assertNotIn(row.part('index'), members)
        self.assertNotIn(row.part('close'), members)

    def test_unmount_retires_a_layout_container_after_its_children_became_roots(self):
        first, second = Square(.5).shift(LEFT), Circle(.3).shift(RIGHT)
        group = VGroup(first, second)
        self.scene.mount_view(group)
        self.assertCountEqual(self.scene.mobjects, [first, second])
        self.scene.unmount_view(group)
        self.assertEqual(self.scene.mobjects, [])
        replacement = group.copy()
        self.scene.mount_view(replacement)
        self.assertTrue(all(part not in self.scene.get_mobject_family_members()
                            for part in group.get_family()))

    def test_retiring_a_group_only_retires_children_that_are_present(self):
        visible, future = Square(.4), Square(.4).shift(RIGHT)
        self.scene.mount_view(visible)
        program = self.start(Retire(VGroup(visible, future)))
        self.assertNotIn(future, self.scene.get_mobject_family_members())
        self.finish(program)
        self.assertEqual(self.scene.mobjects, [])

    def test_extracting_a_named_term_preserves_its_component_references(self):
        row = MathRow({'call':'f(', 'index':'i', 'close':')'})
        old_part = row.part('index')
        self.scene.mount_view(row)
        self.finish(self.start(Move(old_part, MathTex('1').move_to(old_part))))
        self.assertIs(row.part('index'), old_part)
        self.assertIn(old_part, self.scene.get_mobject_family_members())

    def test_later_phases_never_add_their_future_destination_early(self):
        first, second = Square(.5), Circle(.3).shift(RIGHT)
        built = []
        program = self.start(Then(Reveal(first), Later(lambda: (built.append(True) or Replace(first, second)))))
        program.interpolate(.1)
        self.assertEqual(built, [])
        self.assertNotIn(second, self.scene.get_mobject_family_members())
        program.interpolate(.6)
        self.assertEqual(built, [True])
        self.finish(program)
        self.assertEqual(self.scene.mobjects, [second])

    def test_copy_has_a_visible_source_and_one_final_destination_owner(self):
        source = Square(.5).shift(LEFT)
        target = source.copy().shift(3*RIGHT)
        self.scene.mount_view(source)
        points = source.get_all_points().copy()
        program = self.start(CopyInto(source, target))
        program.interpolate(.4)
        np.testing.assert_allclose(source.get_all_points(), points)
        self.assertNotIn(target, self.scene.get_mobject_family_members())
        self.finish(program)
        self.assertCountEqual(self.scene.mobjects, [source, target])
        self.assertEqual(self.scene._view_steps[-1]['operations'], ['copy'])

    def test_definition_copy_replaces_only_the_application(self):
        source, application, result = (Square(.4).shift(LEFT), Circle(.25).shift(RIGHT), Square(.4).shift(RIGHT))
        self.scene.mount_view(source, application)
        program = self.start(ApplyDefinition(source, application, result))
        self.finish(program)
        self.assertCountEqual(self.scene.mobjects, [source, result])
        self.assertEqual(self.scene._view_steps[-1]['operations'], ['definition_copy'])

    def test_stagger_preserves_start_order_and_shares_the_same_view_clock(self):
        first, second = Square(.5), Square(.5).shift(RIGHT)
        program = self.start(Stagger(Reveal(first), Reveal(second), lag_ratio=1))
        program.interpolate(.1)
        self.assertIn(first, self.scene.get_mobject_family_members())
        self.assertNotIn(second, self.scene.get_mobject_family_members())
        self.finish(program)
        self.assertCountEqual(self.scene.mobjects, [first, second])

    def test_attention_does_not_change_the_planned_shape_or_semantic_color(self):
        target = Square(.5)
        self.scene.mount_view(target)
        original = target.get_all_points().copy()
        program = self.start(Pulse(target, trigger='square', reason='Name this square'))
        self.finish(program)
        np.testing.assert_allclose(target.get_all_points(), original)
        self.assertEqual(self.scene._view_steps[-1]['operations'], ['component_effect'])

    def test_a_path_animation_keeps_the_same_object_identity(self):
        car = Square(.4).shift(LEFT)
        self.scene.mount_view(car)
        self.finish(self.start(MoveAlongPath(car, Line(LEFT, RIGHT))))
        self.assertIn(car, self.scene.get_mobject_family_members())
        self.assertAlmostEqual(car.get_x(), 1)

    def test_parallel_additions_do_not_retire_each_others_objects(self):
        left, right = Square(.4).shift(LEFT), Circle(.25).shift(RIGHT)
        self.finish(self.start(Together(Reveal(left), Draw(right))))
        self.assertCountEqual(self.scene.mobjects, [left, right])
        self.assertTrue(all(step['completed'] for step in self.scene._view_steps))

    def test_global_duration_applies_to_each_parallel_operation(self):
        old, new = Square(.4), Circle(.3).shift(RIGHT)
        self.scene.mount_view(old)
        program = self.scene._view_program((Retire(old,run_time=.2), Reveal(new,run_time=1)), 2)
        self.scene.add_mobjects_from_animations([program])
        program._setup_scene(self.scene);program.begin();program.interpolate(.2)
        self.assertGreater(float(old.get_fill_opacity())+float(old.get_stroke_opacity()), .1)
        self.finish(program)

    def test_explicit_clear_then_reveal_keeps_its_authored_phase_ratio(self):
        old, new = Square(.4), Circle(.3).shift(RIGHT)
        self.scene.mount_view(old)
        program = self.scene._view_program((Retire(old,run_time=.2), Reveal(new,run_time=1)),
                                           2, clear_first=True)
        self.scene.add_mobjects_from_animations([program])
        program._setup_scene(self.scene);program.begin();program.interpolate(.1)
        self.assertNotIn(new,self.scene.get_mobject_family_members())
        program.interpolate(.2)
        self.assertIn(new,self.scene.get_mobject_family_members())
        self.finish(program)

    def test_canvas_rejects_two_owners_for_the_same_child(self):
        child = Square(.4)
        canvas = CanvasSlide()
        canvas.include('parent', VGroup(child))
        canvas.include('child', child)
        with self.assertRaisesRegex(ValueError, 'two owners'):
            canvas.validate()

    def test_a_layout_group_can_move_raster_and_vector_children_together(self):
        icon = ImageMobject(np.full((4,4,4),255,dtype=np.uint8)).set_width(.5)
        shape = Square(.4).shift(RIGHT)
        group = Group(icon,shape)
        self.scene.mount_view(group)
        target = group.copy().shift(2*RIGHT)
        self.finish(self.start(Move(group,target)))
        self.assertCountEqual(self.scene.mobjects,[icon,shape])
        np.testing.assert_allclose(icon.get_center(),target[0].get_center())
        np.testing.assert_allclose(shape.get_center(),target[1].get_center())

    def test_group_motion_uses_native_equation_terms_and_adopts_their_new_layout(self):
        row = MathRow({'f': 'f(', 'index': 'i', 'end': ',w)'})
        context = Square(.4).shift(LEFT*2)
        group = VGroup(row,context)
        self.scene.mount_view(group)
        next_row = row.next_layout(index='k+1').shift(RIGHT)
        destination = VGroup(next_row,context.copy().shift(RIGHT))
        program = self.start(Move(group,destination))
        program.interpolate(.4)
        # In transit the real terms are independent roots, not a malformed
        # MathRow whose baseline anchors have morphed into extra glyphs.
        self.assertNotIn(row,self.scene.mobjects)
        self.finish(program)
        self.assertIn(row,self.scene.mobjects)
        self.assertEqual(row.slot_tex['index'],'k+1')
        self.assertEqual(row.native_layout_findings(),[])
        np.testing.assert_allclose(row.get_center(),next_row.get_center())

    def test_equation_motion_applies_the_authored_easing_exactly_once(self):
        row = MathRow({'call': 'f(n)'})
        self.scene.mount_view(row)
        start = row.part('call').get_center().copy()
        target = row.copy().shift(RIGHT*2)
        program = self.start(Move(row,target,rate_func=lambda alpha:alpha**2))
        program.interpolate(.5)
        np.testing.assert_allclose(row.part('call').get_center(),start+RIGHT*.5)
        self.finish(program)

    def test_finished_term_motion_adopts_the_destination_font_calibration(self):
        from algovis.layout import LessonStyle, measured_font_size
        row = MathRow({'index': 'i', 'value': 'v_i'})
        LessonStyle().watch('proof-terms', row)
        destination = row.next_layout(index='k', value='v_k')
        LessonStyle().watch('proof-terms', destination)
        expected = {name: measured_font_size(part) for name, part in destination.parts.items()}
        # The nested phase takes an endpoint snapshot before the whole row is
        # consolidated. Its individual terms must already report correct type.
        for motion in row.motions_to(destination):
            operation = Move(motion.mobject, motion.target_mobject)
            operation.begin()
            operation.finish()
        for name, part in row.parts.items():
            self.assertAlmostEqual(measured_font_size(part), expected[name])


class DefaultAlignmentTests(unittest.TestCase):
    def test_a_column_aligns_new_items_without_offsets(self):
        view = ColumnSlide()
        view.add('short', Text('A short line', font_size=20))
        view.add('long', Text('A significantly longer line', font_size=20))
        self.assertAlmostEqual(view.target('short').get_left()[0], view.target('long').get_left()[0])
        self.assertEqual(view.layout_report()['overrides'], [])

    def test_an_explicit_offset_requires_a_reason_and_warns_once(self):
        view = ColumnSlide()
        view.add('line', Text('A line', font_size=20))
        with self.assertRaisesRegex(ValueError, 'alignment reason'):
            view.offset('line', RIGHT*.1, reason='')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            view.offset('line', RIGHT*.1, reason='Align a deliberately indented continuation')
            view.preview()
        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, LayoutOverrideWarning)
        self.assertEqual(view.layout_report()['overrides'][0]['reason'], 'Align a deliberately indented continuation')

    def test_unexplained_direct_adjustments_are_detected_too(self):
        view = ColumnSlide()
        view.add('line', Text('A line', font_size=20))
        view.target('line').shift(RIGHT*.1)
        with self.assertWarnsRegex(LayoutOverrideWarning, 'Unexplained'):
            view.preview()


if __name__ == '__main__': unittest.main()
