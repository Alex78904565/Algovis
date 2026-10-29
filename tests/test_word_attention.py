import unittest
from unittest.mock import patch
from manim import Square, Wait
from algovis import (ColumnSlide, MathRow, NarrationCue, NarrationTrack, SlideObject,
                     SlideScene, ViewScene, Reveal, Retire, SemanticChange, StateCell)


class WordAttentionTests(unittest.TestCase):
    def setUp(self):
        self.scene = ViewScene()
        self.scene.setup()
        self.addCleanup(self.scene.tear_down)
        self.scene.renderer.time = 0
        self.scene.narration = NarrationTrack('unused.wav', 5,
            [NarrationCue('start',0,'start'), NarrationCue('square',1,'square'), NarrationCue('next',3,'next')],
            words=[{'word':'start','start':0.,'end':.2}, {'word':'square','start':1.,'end':1.2},
                   {'word':'next','start':3.,'end':3.2}])
        self.scene.narration.start_time = 0
        self.calls = []

        def simulate(*animations, **kwargs):
            start = self.scene.renderer.time
            duration = kwargs.get('run_time', max(a.run_time for a in animations))
            for animation in animations:
                self.scene.add_mobjects_from_animations([animation])
                animation._setup_scene(self.scene)
                animation.begin()
            for step in range(41):
                self.scene.renderer.time = start+duration*step/40
                for animation in animations: animation.interpolate(step/40)
            for animation in animations:
                animation.finish()
                animation.clean_up_from_scene(self.scene)
            self.scene.renderer.time = start+duration
            for i, animation in enumerate(animations):
                self.scene._append_review_animation(animation,start,start+duration,0,str(i))

        self.patcher = patch.object(SlideScene, 'play', side_effect=simulate)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def target(self):
        target = Square(.4)
        self.scene.mount_view(target)
        return target

    def callback(self, scene, target):
        self.calls.append(scene.renderer.time)
        return Wait(.4)

    def test_an_object_binding_runs_on_its_word_without_an_explicit_animation_call(self):
        target = self.target()
        SlideObject(target).on_word('square', callback=self.callback, duration=.4, reason='Name the square')
        self.scene.wait(2)
        self.assertEqual(self.calls, [1.])
        self.assertAlmostEqual(self.scene.renderer.time, 2.)

    def test_an_attention_word_inside_an_animation_uses_that_exact_offset(self):
        self.scene.bind_attention(self.target(), 'square', callback=self.callback,
                                  duration=.4, reason='Name the square')
        self.scene.view_on_cue('start', Wait(2), run_time=2, reason='Continue the explanation')
        self.assertEqual(self.calls, [1.])
        records = [a for a in self.scene._review_animations if a.get('cue')=='square']
        # Wait callbacks have no attention bar, but binding timing is still consumed.
        self.assertTrue(self.scene._word_attention[0].fired)

    def test_a_binding_during_the_wait_before_another_cue_does_not_make_that_cue_late(self):
        self.scene.bind_attention(self.target(), 'square', callback=self.callback,
                                  duration=.4, reason='Name the square')
        self.scene.view_on_cue('next', Wait(.5), run_time=.5, reason='Continue')
        self.assertEqual(self.calls, [1.])
        self.assertAlmostEqual(self.scene.renderer.time, 3.5)

    def test_multiple_targets_can_share_the_same_spoken_word(self):
        for _ in range(2):
            self.scene.bind_attention(self.target(), 'square', callback=self.callback,
                                      duration=.4, reason='Compare these objects')
        self.scene.wait(2)
        self.assertEqual(self.calls, [1., 1.])
        self.assertAlmostEqual(self.scene.renderer.time, 2.)

    def test_copies_do_not_inherit_the_originals_automatic_attention(self):
        original = SlideObject(self.target()).on_word('square', callback=self.callback,
                                                      reason='Name it', duration=.4)
        duplicate = original.copy()
        self.scene.mount_view(duplicate.mobject)
        self.scene.wait(2)
        self.assertEqual(self.calls, [1.])

    def test_a_clear_reveal_does_not_receive_an_extra_pulse(self):
        target = Square(.4)
        SlideObject(target).on_word('square', reason='Name it', duration=.4)
        self.scene.view_on_cue('square', Reveal(target), run_time=.6, reason='Reveal the square')
        self.assertTrue(self.scene._word_attention[0].fired)
        self.assertFalse(any(a.get('attention') for a in self.scene._review_animations))

    def test_invalid_or_invisible_targets_fail_instead_of_popping_in(self):
        target = Square(.4)
        self.scene.bind_attention(target, 'square', duration=.4, reason='Name it')
        with self.assertRaisesRegex(ValueError, 'absent'):
            self.scene.view_on_cue('square', run_time=.4, reason='Name it')

    def test_a_binding_cannot_run_past_its_slot_or_silently_miss_the_next_word(self):
        self.scene.bind_attention(self.target(), 'square', duration=.8, reason='Name it')
        with self.assertRaisesRegex(ValueError, 'animation slot'):
            self.scene.view_on_cue('square', run_time=.4, reason='Name it')

    def test_named_equation_terms_choose_a_box_as_the_default(self):
        row = SlideObject(MathRow({'f':'f(', 'index':'i', 'close':')'}))
        term = row.part('index').on_word('square', reason='Name the index', duration=.4)
        self.scene.mount_view(row.mobject)
        self.scene.view_on_cue('square', run_time=.4, reason='Name the index')
        records = [a for a in self.scene._review_animations if a.get('attention')]
        self.assertEqual(records[0]['kind'], 'Circumscribe')
        self.assertEqual(records[0]['wordTiming']['time'], 1.)

    def test_late_registration_fails_instead_of_silently_dropping_attention(self):
        self.scene.renderer.time = 2
        with self.assertRaisesRegex(ValueError, 'after its word was spoken'):
            self.scene.bind_attention(self.target(), 'square', duration=.4, reason='Name it')

    def test_a_structured_layout_transition_also_serves_attention_in_the_preceding_gap(self):
        target = self.target()
        self.scene.bind_attention(target, 'square', callback=self.callback,
                                  duration=.4, reason='Name the square')
        view = ColumnSlide()
        view.add('square', target)
        self.scene.transition_to(view, cue='next', run_time=.5, reason='Move to the next layout')
        self.assertEqual(self.calls, [1.])
        self.assertAlmostEqual(self.scene.renderer.time, 3.5)

    def test_a_cue_is_waited_for_exactly_once(self):
        track = self.scene.narration
        with patch.object(track, 'wait_for_word', wraps=track.wait_for_word) as wait:
            self.scene.view_on_cue('square', Wait(.4), run_time=.4, reason='Continue')
        self.assertEqual(wait.call_count, 1)

    def test_attention_also_runs_inside_a_component_process(self):
        self.scene.bind_attention(self.target(), 'square', callback=self.callback,
                                  duration=.4, reason='Name the square')
        self.scene.animate_view(Wait(2), run_time=2)
        self.assertEqual(self.calls, [1.])
        self.assertAlmostEqual(self.scene.renderer.time, 2.)

    def test_clearing_a_caption_does_not_delay_attention_past_the_trigger_word(self):
        target, old, new = self.target(), Square(.2), Square(.3)
        self.scene.mount_view(old)
        self.scene.bind_attention(target, 'square', callback=self.callback,
                                  duration=.4, reason='Name the square')
        self.scene.transition_view_on_cue('square', Retire(old), Reveal(new),
                                          run_time=.8, reason='Replace the caption')
        self.assertEqual(self.calls, [1.])

    def test_attention_preserves_a_simultaneous_semantic_state_change(self):
        target = StateCell('5')
        self.scene.mount_view(target)
        self.scene.bind_attention(target, 'square', duration=.4, reason='Name the result')
        self.scene.view_on_cue('square', SemanticChange(target,status='computed'),
                               run_time=.4, reason='Compute this state')
        self.assertEqual(target.box.get_stroke_color(), target.theme.success)

    def test_shared_focus_releases_are_also_compiled_into_view_phases(self):
        target = self.target()
        boxes = self.scene.focus_on_cue('square', target, until='next', run_time=.4,
                                       reason='Keep this reference visible')
        self.scene.view_on_cue('next', Wait(.5), run_time=.5, reason='Continue')
        self.assertNotIn(boxes[0], self.scene.get_mobject_family_members())
        releases = [step for step in self.scene._view_steps if step['cue']=='next' and 'retire' in step['operations']]
        self.assertTrue(releases)


if __name__ == '__main__': unittest.main()
