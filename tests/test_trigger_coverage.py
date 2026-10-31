import unittest
from types import SimpleNamespace
from manim import Square
from algovis import LessonAnimation,ColumnSlide,ViewScene
from algovis.review.inspection import trigger_coverage_findings


class TriggerCoverageTests(unittest.TestCase):
    def test_owned_plan_that_never_plays_reports_its_specific_cue(self):
        scene=ViewScene();scene.setup()
        film=scene.lesson_animation()
        film.add(ColumnSlide(),on='first_one',reason='Populate the first base case')
        with self.assertRaisesRegex(RuntimeError,'first_one.*Populate the first base case'):
            scene.validate_trigger_consumption()

    def test_nested_steps_remain_accounted_for(self):
        film=LessonAnimation();group=film.group('the second proof')
        group.add(ColumnSlide(),on='new_hypothesis',reason='State the changed assumption')
        # A mistaken parent cursor must not hide an unplayed child.
        film._played=1
        findings=trigger_coverage_findings({'triggerCoverage':{'steps':film.trigger_coverage()}})
        self.assertEqual(findings[0]['cue'],'new_hypothesis')
        self.assertEqual(findings[0]['kind'],'declared_animation_never_consumed')

    def test_a_played_plan_consumes_registered_leaf_steps(self):
        class Renderer:
            def register_animation_plan(self,plan):self.plan=plan
            def transition_to(self,*args,**kwargs):pass
            def transition_phase(self,*args,**kwargs):pass
        renderer=Renderer();film=LessonAnimation(renderer)
        film.group('one explanation').add(ColumnSlide(),on='base',reason='State the base case')
        film.play(renderer)
        records=film.trigger_coverage()
        self.assertTrue(records[0]['consumed'])
        self.assertEqual(trigger_coverage_findings({'triggerCoverage':{'steps':records}}),[])

    def test_registered_plan_cannot_be_silently_consumed_by_another_scene(self):
        owner=SimpleNamespace(register_animation_plan=lambda plan:None)
        film=LessonAnimation(owner)
        with self.assertRaisesRegex(ValueError,'owning scene'):film.play(object())

    def test_an_unfired_attention_binding_is_not_lost_at_teardown(self):
        scene=ViewScene();scene.setup()
        binding=scene.bind_attention(Square(),cue='smaller_input',reason='Point to the assumed child')
        with self.assertRaisesRegex(RuntimeError,'smaller_input'):scene.validate_trigger_consumption()
        binding.fired=True
        scene.validate_trigger_consumption()

    def test_changing_narration_cannot_discard_an_unfired_binding(self):
        scene=ViewScene();scene.setup()
        scene.bind_attention(Square(),cue='old_phrase',reason='Explain this object')
        scene.narration=SimpleNamespace()
        with self.assertRaisesRegex(RuntimeError,'old_phrase'):
            scene.begin_narration('a-new-recording.json')

    def test_manifest_reports_both_missing_step_and_attention_executions(self):
        manifest={'triggerCoverage':{'steps':[{'cue':'rewrite','consumed':False,'reason':'Apply the hypothesis'}],
            'attention':[{'cue':'indices','consumed':False,'reason':'Name these arguments'}]}}
        self.assertEqual([f['kind'] for f in trigger_coverage_findings(manifest)],
            ['declared_animation_never_consumed','declared_attention_never_consumed'])

    def test_existing_manifests_are_readable_without_inventing_coverage(self):
        self.assertEqual(trigger_coverage_findings({'snapshots':[]}),[])
