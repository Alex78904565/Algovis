import unittest
from unittest.mock import patch

import numpy as np
from manim import DOWN, Group, Rectangle, Scene, Square, Text, VGroup

from algovis import (ApplyDefinition, ColumnSlide, EquationFrame, EquationSlide, MathRow, NarrationCue,
                     NarrationTrack, ProofSlide, SlideObject, SlideScene,
                     SlideView, SplitSlide, ViewTransition)


def start(animation, scene):
    scene.add_mobjects_from_animations([animation])
    animation._setup_scene(scene)
    animation.begin()


def finish(animation, scene):
    animation.interpolate(1)
    animation.finish()
    animation.clean_up_from_scene(scene)


def apply(plan, scene):
    for animation in plan.animations(scene):
        start(animation, scene)
        finish(animation, scene)
    plan.commit(scene)


class LayoutPlanningTests(unittest.TestCase):
    def test_future_views_and_their_copies_do_not_move_visible_artwork(self):
        live = Square(.7).shift([2, -1, 0])
        points = live.get_all_points().copy()
        first = ColumnSlide('A definition')
        obj = first.add('source', live)
        second = SplitSlide(first.object('title'))
        second.add('source', obj)
        copied = obj.copy()
        second.add('application', copied, column='right')
        self.assertIsNot(copied.mobject, live)
        self.assertIs(copied.copied_from, obj)
        np.testing.assert_allclose(live.get_all_points(), points)
        np.testing.assert_allclose(copied.mobject.get_all_points(), points)
        self.assertIs(first.fork().object('source'), obj)
        self.assertGreater(second.target('application').get_x(), 0)

    def test_fork_edits_are_detached_and_keep_the_function_at_its_left_anchor(self):
        row = MathRow({'function': 'f(', 'argument': 'i', 'close': ')'})
        first = ColumnSlide()
        handle = first.add('equation', row)
        second = first.fork().substitute('equation', argument='i+1')
        self.assertIs(second.object('equation'), handle)
        self.assertEqual(first.target('equation').slot_tex['argument'], 'i')
        self.assertEqual(row.slot_tex['argument'], 'i')
        self.assertAlmostEqual(first.target('equation').get_left()[0],
                               second.target('equation').get_left()[0])
        self.assertEqual(second.target('equation').native_layout_findings(), [])

    def test_nested_columns_place_rows_without_global_coordinates_or_shrinking(self):
        view = SplitSlide(weights=(2, 1))
        first = Square(.8)
        view.add('first', first)
        view.add('second', Square(.5))
        view.add('right', Square(.5), column='right')
        a, b = view.target('first'), view.target('second')
        self.assertAlmostEqual(a.get_left()[0], b.get_left()[0])
        self.assertGreater(a.get_bottom()[1], b.get_top()[1])
        self.assertAlmostEqual(a.width, first.width)
        self.assertGreater(view.target('right').get_left()[0], a.get_right()[0])

    def test_simplifying_a_fraction_preserves_its_baseline_and_the_next_row(self):
        view = ColumnSlide()
        view.add('equation', MathRow({'call': 'f(3)', 'eq': '=', 'value': r'\frac{3(3+1)}2'}))
        view.add('note', Text('The answer', font_size=20))
        simplified = view.fork().substitute('equation', value='6')
        self.assertAlmostEqual(view.target('equation').baseline, simplified.target('equation').baseline)
        np.testing.assert_allclose(view.target('note').get_center(), simplified.target('note').get_center())

    def test_proof_substitution_keeps_the_unchanged_function_on_its_baseline(self):
        view = ProofSlide()
        view.add('inductive_step', MathRow({'call': 'f(k+1)', 'eq': '=', 'child': 'f(k)', 'rest': '+(k+1)'}))
        expanded = view.fork().substitute('inductive_step', child=r'\frac{k(k+1)}2')
        self.assertAlmostEqual(view.target('inductive_step').baseline, expanded.target('inductive_step').baseline)

    def test_failed_add_move_and_substitution_leave_the_plan_unchanged(self):
        view = ColumnSlide()
        view.add('first', Square(.5))
        before = view.target('first').get_all_points().copy()
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            view.add('too_big', Square(9))
        self.assertEqual(list(view.items), ['first'])
        np.testing.assert_allclose(view.target('first').get_all_points(), before)
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            view.move('first', region='missing')
        self.assertEqual(view.items['first'].slot, 'body')
        np.testing.assert_allclose(view.target('first').get_all_points(), before)
        equation = ColumnSlide()
        equation.add('row', MathRow({'value': '1'}))
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            equation.substitute('row', value='+'.join(['1']*100))
        self.assertEqual(equation.target('row').slot_tex, {'value': '1'})

    def test_duplicate_ownership_and_overlapping_logical_items_fail_early(self):
        child = Square(.5)
        view = SplitSlide()
        view.add('parent', VGroup(child))
        with self.assertRaisesRegex(ValueError, 'group and its child'):
            view.add('child', child, column='right')
        view = SlideView()
        view.add('one', Square(.5))
        with self.assertRaisesRegex(ValueError, 'overlap'):
            view.add('two', Square(.5))
        self.assertEqual(list(view.items), ['one'])

    def test_preview_is_independent_of_both_the_live_object_and_planned_art(self):
        view = ColumnSlide()
        obj = view.add('box', Square(.5))
        preview = view.preview()
        preview.shift(DOWN)
        self.assertNotAlmostEqual(preview[0].get_y(), view.target('box').get_y())
        self.assertNotAlmostEqual(preview[0].get_y(), obj.mobject.get_y())

    def test_proof_rows_reuse_the_standard_frame_and_align_labels_to_first_lines(self):
        view = ProofSlide('Induction')
        lines = VGroup(Text('Assume the smaller answer works', font_size=20),
                       Text('for every smaller input', font_size=20)).arrange(DOWN)
        view.add('induction_hypothesis', lines)
        self.assertAlmostEqual(view.target('label:induction_hypothesis').get_top()[1],
                               view.target('induction_hypothesis')[0].get_top()[1])
        self.assertAlmostEqual(view.target('induction_hypothesis').get_left()[0],
                               view.frame.left[0])
        with self.assertRaisesRegex(ValueError, 'Duplicate proof row'):
            view.add('INDUCTION HYPOTHESIS', Square(.5))
        changed = view.fork().remove('induction_hypothesis')
        self.assertIn('induction_hypothesis', view.items)
        self.assertNotIn('label:induction_hypothesis', changed.items)

    def test_equation_slides_reuse_named_frame_rows_and_keep_prior_equations(self):
        view = EquationSlide('A recurrence')
        row = view.add('recurrence', MathRow({'function': 'f(n)', 'eq': '=', 'value': 'f(n-1)+n'}))
        view.add('base', MathRow({'base': 'f(0)=0'}))
        self.assertIsInstance(view.frame, EquationFrame)
        self.assertAlmostEqual(view.target('recurrence').get_left()[0], view.frame.left[0])
        self.assertAlmostEqual(view.target('base').get_left()[0], view.frame.left[0])
        second = view.fork().substitute('recurrence', function='f[n]', value='f[n-1]+n')
        self.assertIs(second.object('recurrence'), row)
        self.assertIs(second.object('base'), view.object('base'))
        with self.assertRaisesRegex(ValueError, 'Unknown equation row'):
            view.add('made_up', Square(.5))


class ViewTransitionTests(unittest.TestCase):
    def test_retained_identity_moves_and_unchanged_objects_get_no_animation(self):
        first = ColumnSlide()
        source = first.add('box', Square(.7))
        scene = Scene()
        first.install(scene)
        no_change = ViewTransition(first, first.fork())
        self.assertEqual(no_change.describe()['keep'], ['box'])
        self.assertEqual(no_change.animations(scene), ())
        second = SplitSlide()
        second.add('box', source, column='right')
        plan = ViewTransition(first, second)
        self.assertEqual(plan.describe()['move'], ['box'])
        points = source.mobject.get_all_points().copy()
        animation, = plan.animations(scene)
        np.testing.assert_allclose(source.mobject.get_all_points(), points)
        start(animation, scene)
        animation.interpolate(.5)
        x = source.mobject.get_x()
        self.assertGreater(x, first.target('box').get_x())
        self.assertLess(x, second.target('box').get_x())
        finish(animation, scene)
        plan.commit(scene)
        self.assertEqual(scene.mobjects, [source.mobject])
        np.testing.assert_allclose(source.mobject.get_all_points(), second.target('box').get_all_points())

    def test_copy_travels_from_visible_source_and_the_original_stays_put(self):
        first = SplitSlide()
        source = first.add('source', Square(.7))
        copied = source.copy()
        second = first.fork()
        second.add('copy', copied, column='right')
        scene = Scene()
        first.install(scene)
        original = source.mobject.get_all_points().copy()
        plan = ViewTransition(first, second)
        animation, = plan.animations(scene)
        self.assertNotIn(copied.mobject, scene.get_mobject_family_members())
        start(animation, scene)
        transfer = animation.animation.animations[0]
        self.assertIsInstance(transfer, ApplyDefinition)
        np.testing.assert_allclose(transfer.traveller.get_center(), source.mobject.get_center())
        animation.interpolate(.4)
        self.assertGreater(transfer.traveller.get_x(), source.mobject.get_x())
        self.assertNotIn(copied.mobject, scene.get_mobject_family_members())
        np.testing.assert_allclose(source.mobject.get_all_points(), original)
        finish(animation, scene)
        plan.commit(scene)
        self.assertEqual(scene.mobjects, [source.mobject, copied.mobject])
        self.assertNotIn(transfer.traveller, scene.get_mobject_family_members())
        self.assertAlmostEqual(copied.mobject.get_x(), second.target('copy').get_x())

    def test_future_equation_stays_absent_during_the_exit_phase(self):
        first = ColumnSlide()
        old = first.add('old', Square(.7))
        second = ColumnSlide()
        new = second.add('new', MathRow({'call': 'f(3)', 'eq': '=', 'value': '6'}))
        scene = Scene()
        first.install(scene)
        plan = ViewTransition(first, second)
        animation, = plan.animations(scene)
        old_points = new.mobject.get_all_points().copy()
        start(animation, scene)
        animation.interpolate(.12)
        self.assertNotIn(new.mobject, scene.get_mobject_family_members())
        np.testing.assert_allclose(new.mobject.get_all_points(), old_points)
        animation.interpolate(.4)
        self.assertNotIn(old.mobject, scene.get_mobject_family_members())
        finish(animation, scene)
        plan.commit(scene)
        self.assertEqual(scene.mobjects, [new.mobject])
        self.assertEqual(new.mobject.native_layout_findings(), [])
        self.assertEqual(new.mobject.slot_tex['value'], '6')

    def test_copying_an_equation_keeps_its_named_terms_and_native_geometry(self):
        first = SplitSlide()
        source = first.add('definition', MathRow({'call': 'f(k)', 'eq': '=', 'value': r'\frac{k(k+1)}2'}))
        copied = source.copy()
        second = first.fork()
        second.add('application', copied, column='right')
        second.substitute('application', call='f(3)', value=r'\frac{3(3+1)}2')
        scene = Scene()
        first.install(scene)
        apply(ViewTransition(first, second), scene)
        self.assertEqual(copied.mobject.slot_tex['call'], 'f(3)')
        self.assertEqual(source.mobject.slot_tex['call'], 'f(k)')
        self.assertEqual(copied.mobject.native_layout_findings(), [])
        self.assertIs(copied.mobject.part('value'), copied.mobject[2])
        third = second.fork().substitute('application', value='6')
        old_parts = dict(copied.mobject.parts)
        apply(ViewTransition(second, third), scene)
        self.assertEqual(copied.mobject.parts, old_parts)
        self.assertEqual(copied.mobject.slot_tex['value'], '6')
        self.assertEqual(copied.mobject.native_layout_findings(), [])

    def test_proof_substitution_carries_only_the_named_definition_term(self):
        first = ProofSlide('Induction')
        definition = first.add('induction_hypothesis', MathRow({'call': 'f(k)', 'eq': '=', 'value': r'\frac{k(k+1)}2'}))
        row = first.add('inductive_step', MathRow({'call': 'f(k+1)', 'eq': '=', 'child': 'f(k)', 'rest': '+(k+1)'}))
        scene = Scene()
        first.install(scene)
        source_points = definition.mobject.get_all_points().copy()
        parts = dict(row.mobject.parts)
        second = first.fork().substitute('inductive_step', child=r'\frac{k(k+1)}2',
                                       from_definition=definition.part('value'))
        plan = ViewTransition(first, second)
        animation, = plan.animations(scene)
        start(animation, scene)
        transfer = next(a for a in animation.animation.animations if isinstance(a, ApplyDefinition))
        self.assertIs(transfer.definition, definition.mobject.part('value'))
        self.assertIs(transfer.application, row.mobject.part('child'))
        animation.interpolate(.5)
        np.testing.assert_allclose(definition.mobject.get_all_points(), source_points)
        finish(animation, scene)
        plan.commit(scene)
        self.assertEqual(row.mobject.parts, parts)
        self.assertEqual(row.mobject.native_layout_findings(), [])
        self.assertEqual(row.mobject.slot_tex['child'], r'\frac{k(k+1)}2')
        self.assertEqual(len(scene.mobjects), len(second.items))
        self.assertNotIn(transfer.traveller, scene.get_mobject_family_members())

    def test_a_retired_copy_source_remains_until_its_copy_arrives(self):
        first = ColumnSlide()
        source = first.add('source', Square(.5))
        second = ColumnSlide()
        copied = second.add('copy', source.copy())
        scene = Scene()
        first.install(scene)
        plan = ViewTransition(first, second)
        animation, = plan.animations(scene)
        start(animation, scene)
        animation.interpolate(.4)
        self.assertIn(source.mobject, scene.get_mobject_family_members())
        finish(animation, scene)
        plan.commit(scene)
        self.assertEqual(scene.mobjects, [copied.mobject])

    def test_missing_copy_sources_fail_and_layout_children_can_be_retained_independently(self):
        first = ColumnSlide()
        source = SlideObject(Square(.5))
        second = ColumnSlide()
        second.add('copy', source.copy())
        with self.assertRaisesRegex(ValueError, 'source must already be visible'):
            ViewTransition(first, second).animations(Scene())
        child = Square(.5)
        first.add('parent', VGroup(child))
        second = ColumnSlide()
        second.add('child', child)
        scene = Scene()
        first.install(scene)
        plan = ViewTransition(first, second)
        apply(plan, scene)
        self.assertEqual(scene.mobjects, [child])

    def test_children_keep_identity_when_layout_groups_change_between_views(self):
        first, second = ColumnSlide(), SplitSlide()
        a, b = Square(.5), Square(.4)
        first.add('together', VGroup(a,b).arrange([1,0,0],buff=.3))
        second.add('left', VGroup(a))
        second.add('right', VGroup(b),column='right')
        scene = Scene()
        first.install(scene)
        plan = ViewTransition(first, second)
        self.assertEqual(set(plan.retained), {id(a),id(b)})
        apply(plan, scene)
        self.assertIn(a, scene.get_mobject_family_members())
        self.assertIn(b, scene.get_mobject_family_members())
        self.assertAlmostEqual(a.get_x(), second.target('left')[0].get_x())
        self.assertAlmostEqual(b.get_x(), second.target('right')[0].get_x())

    def test_removing_everything_leaves_no_hidden_group_or_lingering_descendants(self):
        first = ColumnSlide('Heading')
        first.add('group', VGroup(Square(.3), Square(.3).shift([1, 0, 0])))
        scene = Scene()
        first.install(scene)
        apply(ViewTransition(first, ColumnSlide()), scene)
        self.assertEqual(scene.mobjects, [])


class SceneCompositionTests(unittest.TestCase):
    def scene(self):
        scene = SlideScene()
        scene.setup()
        self.addCleanup(scene.tear_down)
        return scene

    def test_set_view_retains_external_markers_and_saves_a_detached_outgoing_layout(self):
        scene = self.scene()
        marker = Rectangle(width=.2, height=.1).shift([0, 3.5, 0])
        scene.add(marker)
        view = ColumnSlide()
        obj = view.add('box', Square(.5))
        scene.set_view(view)
        view.remove('box')
        self.assertIn('box', scene.current_view.items)
        scene.set_view(ColumnSlide())
        self.assertEqual(scene.mobjects, [marker])
        self.assertNotIn(obj.mobject, scene.mobjects)

    def test_narrated_transition_waits_for_the_verified_word_before_preparing_entries(self):
        scene = self.scene()
        scene.renderer.time = 0
        scene.narration = NarrationTrack('unused.wav', 5, [NarrationCue('apply', 2, 'apply')],
                                        words=[{'word': 'apply', 'start': 2., 'end': 2.4}])
        scene.narration.start_time = 0
        scene.require_word_timing = True
        view = ColumnSlide()
        row = view.add('equation', MathRow({'value': '6'}))
        initial = row.mobject.get_center().copy()
        calls = []

        def wait(duration):
            calls.append(('wait', scene.renderer.time, duration))
            np.testing.assert_allclose(row.mobject.get_center(), initial)
            self.assertNotIn(row.mobject, scene.get_mobject_family_members())
            scene.renderer.time += duration

        def play(*animations, **options):
            calls.append(('play', scene.renderer.time, options['run_time']))
            self.assertIn('wordTiming', scene._review_active_cue)
            for animation in animations:
                start(animation, scene)
                finish(animation, scene)
            scene.renderer.time += options['run_time']

        with patch.object(scene, 'wait', wait), patch.object(scene, 'play', play):
            scene.transition_to(view, cue='apply', run_time=.8, reason='Apply the definition')
        self.assertEqual(calls, [('wait', 0, 2.), ('play', 2., .8)])
        self.assertEqual(row.mobject.native_layout_findings(), [])
        self.assertIs(scene.current_view.object('equation'), row)

    def test_missing_word_or_reason_cannot_silently_fall_back_to_untimed_play(self):
        scene = self.scene()
        scene.narration = object()
        with self.assertRaisesRegex(ValueError, 'spoken cue'):
            scene.transition_to(ColumnSlide())
        with self.assertRaisesRegex(ValueError, 'instructional reason'):
            scene.transition_to(ColumnSlide(), cue='apply')

    def test_existing_cue_helper_dispatches_views_without_losing_the_word_or_reason(self):
        scene = self.scene()
        view = ColumnSlide()
        with patch.object(scene, 'transition_to') as transition:
            scene.transition_on_cue('apply', view, run_time=.7, reason='Use the definition', edge='end')
            transition.assert_called_once_with(view, cue='apply', run_time=.7,
                                               reason='Use the definition', edge='end')

    def test_mixing_legacy_slide_lifecycle_cannot_silently_leave_a_view_on_screen(self):
        scene = self.scene()
        view = ColumnSlide()
        view.add('box', Square(.5))
        scene.set_view(view)
        with self.assertRaisesRegex(ValueError, 'planned view is active'):
            scene.begin_slide('A legacy slide')

    def test_legacy_transition_still_accepts_existing_animation_calls(self):
        from manim import FadeIn
        scene = self.scene()
        with patch.object(scene, 'play') as play:
            animation = FadeIn(Square(.5))
            scene.transition(animation, run_time=.3)
            self.assertIs(play.call_args.args[0], animation)

    def test_deferred_transition_frames_match_a_fresh_draw_without_stale_text(self):
        scene = self.scene()
        first = SplitSlide()
        source = first.add('source', Square(.5))
        scene.set_view(first)
        second = first.fork()
        second.add('copy', source.copy(), column='right')
        plan = ViewTransition(scene.current_view, second)
        scene.animations = list(plan.animations(scene))
        scene._view_transition_active = True
        self.addCleanup(setattr, scene, '_view_transition_active', False)
        scene.begin_animations()
        self.assertEqual(scene.static_mobjects, [])
        scene.renderer.save_static_frame_data(scene, scene.static_mobjects)
        scene.update_to_time(.45)
        scene.renderer.update_frame(scene, mobjects=scene.moving_mobjects, ignore_skipping=True)
        actual = scene.renderer.get_frame().copy()
        scene.renderer.static_image = None
        scene.renderer.update_frame(scene, ignore_skipping=True)
        np.testing.assert_array_equal(actual, scene.renderer.get_frame())
        for animation in scene.animations:
            finish(animation, scene)
        plan.commit(scene)

    def test_review_duration_bars_expose_the_actual_copy_not_just_its_deferred_wrapper(self):
        scene = self.scene()
        first = SplitSlide()
        source = first.add('source', Square(.5))
        scene.set_view(first)
        second = first.fork()
        second.add('copy', source.copy(), column='right')
        plan = ViewTransition(scene.current_view, second)
        animation, = plan.animations(scene)
        start(animation, scene)
        finish(animation, scene)
        scene._append_review_animation(animation, 2, 3, 0, '1')
        self.assertEqual([item['kind'] for item in scene._review_animations], ['ApplyDefinition'])
        self.assertEqual(scene._review_animations[0]['start'], 2)
        self.assertEqual(scene._review_animations[0]['end'], 3)
        plan.commit(scene)


if __name__ == '__main__':
    unittest.main()
