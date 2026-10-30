import unittest
from types import SimpleNamespace
import numpy as np
from manim import Rectangle
from algovis import (Equation,ListScene,ProofSlide,SceneSequence,LessonAnimation,TextObject,MathStack,ConversionScene,MapScene)
from algovis.animation import SceneBeat


class SequenceLayoutTests(unittest.TestCase):
    def test_list_and_block_share_the_centered_common_edge_contract(self):
        from algovis import BlockScene
        from manim import Group
        for layout in (ListScene,BlockScene):
            first=layout();first.add('first',TextObject('A short starting row.'))
            last=first.fork();last.add('second',TextObject('The longer completed argument.'))
            sequence=SceneSequence('the complete argument')
            sequence.add(first,reason='Begin');sequence.add(last,reason='Complete');sequence.compile()
            a,b=[beat.scene for beat in sequence.beats]
            body=Group(*(item.target for item in b.items.values() if item.slot=='body'))
            np.testing.assert_allclose(body.get_center(),b.layout.body.center,atol=1e-7)
            self.assertAlmostEqual(b.target('first').get_left()[0],b.target('second').get_left()[0])
            np.testing.assert_allclose(a.target('first').get_center(),b.target('first').get_center())

    def test_paired_argument_is_centered_as_a_whole_without_losing_row_alignment(self):
        from algovis import PairedScene
        from manim import Group
        first=PairedScene(pairs=(('step1','example1'),('step2','example2')))
        first.add('step1',TextObject('Choose a smaller instance'),slot='left')
        first.add('step2',TextObject('Assume it works'),slot='left')
        last=first.fork();last.add('example1',Equation({'f':'f(n-1)'}),slot='right')
        last.add('example2',Equation({'f':'f(n-1)=1+2+\\cdots+(n-1)'}),slot='right')
        sequence=SceneSequence('Paired explanation');sequence.add(first,reason='Recipe');sequence.add(last,reason='Examples');sequence.compile()
        a,b=[beat.scene for beat in sequence.beats]
        art=Group(*(item.target for item in b.items.values()))
        np.testing.assert_allclose(art.get_center(),b.layout.body.center,atol=1e-7)
        np.testing.assert_allclose(a.target('step1').get_center(),b.target('step1').get_center())
        for left,right in b.pairs:self.assertAlmostEqual(b.target(left).get_top()[1],b.target(right).get_top()[1])

    def test_continuing_proof_equality_aligns_its_operator_with_the_previous_line(self):
        view=ProofSlide()
        view.add('inductive_step',Equation({'call':'f(k+1)','eq':'=','child':'f(k)','plus':'+','n':'(k+1)'}))
        view.add('work',Equation({'eq':'=','child':r'1+2+\cdots+k','plus':'+','n':'(k+1)'}))
        self.assertAlmostEqual(view.target('work').part('eq').get_left()[0],view.target('inductive_step').part('eq').get_left()[0])
        self.assertNotIn('call',view.target('work').parts)
        view.validate()

    def test_new_terms_follow_the_declared_completed_status_in_an_edited_equation(self):
        first=ListScene();first.add('base',Equation({'call':'f(0)'},role='current'))
        completed=first.fork().revise('base',{'call':'f(0)','eq':'=','zero':'0'}).set_meaning('base',status='computed')
        final=completed.fork().revise('base',{'call':'f(0)','eq':'=','zero':'0','consequence':r'\Longrightarrow P(0)'})
        self.assertEqual(final.target('base').part('consequence').get_color(),final.theme.success)

    def test_paired_explanations_share_row_tops_and_reserve_later_multiline_examples(self):
        from algovis import PairedScene
        first=PairedScene(pairs=(('step1','example1'),('step2','example2')))
        first.add('step1',TextObject('Choose a smaller input'),slot='left')
        first.add('step2',TextObject('Assume its answer'),slot='left')
        later=first.fork()
        later.add('example1',TextObject('A longer example\nwith two lines.'),slot='right')
        later.add('example2',Equation({'f':'f(n-1)'}),slot='right')
        group=SceneSequence('Paired recipe')
        group.add(first,reason='Show the recipe');group.add(later,reason='Apply each step');group.compile()
        a,b=[beat.scene for beat in group.beats]
        for name in ('step1','step2'):np.testing.assert_allclose(a.target(name).get_center(),b.target(name).get_center())
        from algovis.core.proof import first_line_of
        for left,right in first.pairs:
            self.assertAlmostEqual(first_line_of(b.target(left)).get_top()[1],first_line_of(b.target(right)).get_top()[1])
        b.validate()

    def test_proof_consequence_is_centered_beyond_the_proof_rail(self):
        view=ProofSlide('A proof')
        view.add('claim',TextObject('The claim holds.'))
        view.add('conclusion',Equation({'conclusion':r'P(n)\text{ holds for all }n\ge0'}))
        conclusion=view.target('conclusion');rail=view.target('proof_rail')
        self.assertAlmostEqual(conclusion.get_x(),view.layout.footer.center[0])
        self.assertLess(conclusion.get_top()[1],rail.get_bottom()[1])
        view.validate()

    def test_compact_argument_reserves_future_height_and_centers_the_completed_block(self):
        from algovis import BlockScene
        from manim import Group
        first=BlockScene();first.add('work',Equation({'f':'f(n)'}))
        last=first.fork();last.add('meaning',TextObject('A lower bound on the number of operations.'))
        group=SceneSequence('One compact argument')
        group.add(first,reason='State the work');group.add(last,reason='Explain the bound');group.compile()
        a,b=[beat.scene for beat in group.beats]
        np.testing.assert_allclose(a.target('work').get_center(),b.target('work').get_center())
        art=Group(*(item.target for item in b.items.values()))
        np.testing.assert_allclose(art.get_center(),b.layout.body.center)
        self.assertAlmostEqual(b.target('work').get_left()[0],b.target('meaning').get_left()[0])

    def test_filling_illustration_follows_its_text_column_without_stretching_label_type(self):
        from algovis import ComparisonScene,ServerRacks
        from algovis.layout import measured_font_size
        first=ComparisonScene(center_blocks=True)
        first.add('machine',ServerRacks('COMPUTER'),slot='left',fill='width')
        last=first.fork();last.add('speed',Equation({'speed':r'1.742\times10^{18}\ \mathrm{FLOPS}'}),slot='left')
        last.add('description',TextObject('floating-point operations per second',type_role='note'),slot='left')
        last.add('calculation',Equation({'years':r'17.6\times10^{12}'}),slot='right')
        group=SceneSequence('The complete calculation')
        group.add(first,reason='Show the computer');group.add(last,reason='Give its speed and runtime');group.compile()
        a,b=[beat.scene for beat in group.beats]
        width=max(b.target(name).width for name in ('speed','description'))
        self.assertAlmostEqual(b.target('machine')[0].width,width)
        np.testing.assert_allclose(a.target('machine').get_center(),b.target('machine').get_center())
        self.assertAlmostEqual(measured_font_size(b.target('machine').label),b.typography.label)
        for view in (a,b):view.validate()

    def test_definition_rows_are_left_aligned_inside_a_centered_block(self):
        from algovis import DefinitionScene
        view=DefinitionScene()
        view.add('label',TextObject('A rule',type_role='note'),slot='explanation')
        view.add('meaning',TextObject('A longer definition of the function.'),slot='explanation')
        view.add('base',Equation({'base':'f(1)=1'}),slot='explanation')
        rows=[view.target(name) for name in ('label','meaning','base')]
        self.assertTrue(all(abs(row.get_left()[0]-rows[0].get_left()[0])<1e-7 for row in rows))
        left=min(row.get_left()[0] for row in rows);right=max(row.get_right()[0] for row in rows)
        self.assertAlmostEqual((left+right)/2,view._region('explanation').center[0])
        view.validate()

    def test_future_block_width_reserves_a_stable_left_anchor_before_reveal(self):
        from algovis import DefinitionScene
        first=DefinitionScene()
        source=first.add('base',Equation({'base':'f(1)=1'}),slot='explanation')
        source_position=source.mobject.get_center().copy()
        later=first.fork()
        later.add('meaning',TextObject('The answer for this input is the sum of its two children.'),slot='explanation')
        group=SceneSequence('A complete function definition')
        group.add(first,reason='Introduce the base case')
        group.add(later,reason='Explain how to construct the other cases')
        group.compile()
        a,b=[beat.scene for beat in group.beats]
        self.assertNotIn('meaning',a.items)
        self.assertAlmostEqual(a.target('base').get_left()[0],b.target('base').get_left()[0])
        left=min(item.target.get_left()[0] for item in b.items.values())
        right=max(item.target.get_right()[0] for item in b.items.values())
        self.assertAlmostEqual((left+right)/2,b._region('explanation').center[0])
        np.testing.assert_allclose(source.mobject.get_center(),source_position)
        self.assertIn('DefinitionScene/explanation',group.layout_report['blockWidths'])

    def test_cross_column_definition_copy_avoids_the_example_artwork(self):
        from algovis import ComparisonScene
        first=ComparisonScene()
        first.add('art',Rectangle(width=4,height=2),slot='left')
        source=first.add('stored',Equation({'value':'2'}),slot='left')
        first.add('result',Equation({'value':'2'}),slot='right')
        # The public route is geometry based and does not mutate either view.
        start=first.target('stored');destination=first.target('result')
        source.mobject.move_to(start)
        route=first.definition_route(source.mobject,destination)
        self.assertEqual(len(route),2)
        self.assertAlmostEqual(route[0][0],route[1][0])
        self.assertAlmostEqual(route[0][1],start.get_y())
        self.assertAlmostEqual(route[1][1],destination.get_y())

    def test_proof_conclusion_shares_the_body_fit_across_all_steps(self):
        from algovis.layout import measured_font_size
        first=ProofSlide('A complete proof')
        first.add('claim',TextObject('The formula holds.'))
        second=first.fork()
        second.add('inductive_step',TextObject('Assume the preceding value is correct. Use it to obtain the next value.'))
        second.add('conclusion',TextObject('Therefore the formula holds for every non-negative input.'))
        group=SceneSequence('proof including its conclusion')
        group.add(first,reason='State the claim');group.add(second,reason='Finish the proof')
        group.compile()
        final=group.beats[-1].scene
        self.assertAlmostEqual(measured_font_size(final.target('claim')),
                               measured_font_size(final.target('conclusion')))

    def test_proof_definition_copy_routes_beside_intervening_claim_and_base(self):
        proof=ProofSlide('A proof',profile='worked')
        source=proof.add('definitions',Equation({'child':'f(n-1)','plus':'+','n':'n'}))
        proof.add('claim',Equation({'statement':r'P(n):f(n)=1+2+\cdots+n'}))
        proof.add('base_case',Equation({'statement':'f(0)=0'}))
        proof.add('induction_hypothesis',Equation({'statement':r'f(k)=1+2+\cdots+k'}))
        proof.add('inductive_step',Equation({'call':'f(k+1)','eq':'=','child':'f(n-1)'}))
        from manim import Scene
        proof.install(Scene())
        destination=proof.target('inductive_step').part('child')
        route=proof.definition_route(source.mobject.part('child'),destination)
        self.assertEqual(len(route),2)
        half_width=max(source.mobject.part('child').width,destination.width)/2
        for name in ('claim','base_case','induction_hypothesis'):
            self.assertGreater(route[0][0]-half_width,proof.target(name).get_right()[0])
        self.assertLess(route[0][0]+half_width,proof.layout.body.width/2)

    def test_a_concrete_example_stays_centered_as_its_definition_grows(self):
        first=MapScene('A journey')
        first.add('map',Rectangle(width=6,height=2),slot='map')
        second=first.fork();second.add('capacity',TextObject('Capacity: two units'),slot='meaning')
        second.add('roads',TextObject('Each road uses one unit'),slot='meaning')
        sequence=SceneSequence('One example')
        sequence.add(first,reason='Introduce the map');sequence.add(second,reason='Give the instance data')
        sequence.compile()
        a,b=[beat.scene for beat in sequence.beats]
        np.testing.assert_allclose(a.target('map').get_center(),b.target('map').get_center())
        self.assertAlmostEqual(a.target('map').get_x(),a.layout.body.center[0])
        self.assertAlmostEqual(a.target('map').width,b.target('map').width)

    def test_conversion_connector_tracks_the_call_row_without_consuming_a_cost_row(self):
        view=ConversionScene('Conversion')
        view.add('source',MathStack(TextObject('FUNCTION'),Equation({'call':'f(n)'})),slot='left')
        view.add('connector',Equation({'arrow':r'\Longrightarrow'}),slot='connector')
        view.add('destination',MathStack(TextObject('ARRAY'),Equation({'call':'f[n]'})),slot='right')
        before=view.target('connector').get_center().copy()
        view.add('source_cost',Equation({'cost':r'\Omega(1.6^n)'}),slot='left')
        view.add('destination_cost',Equation({'cost':'O(n)'}),slot='right')
        view.validate()
        np.testing.assert_allclose(view.target('connector').get_center(),before)
        self.assertAlmostEqual(view.target('source')[1].baseline,view.target('connector').baseline)
        self.assertAlmostEqual(view.target('destination')[1].baseline,view.target('connector').baseline)
        self.assertAlmostEqual(view.target('source_cost').baseline,view.target('destination_cost').baseline)
        self.assertAlmostEqual(before[0]-view.target('source')[1].get_x(),
                               view.target('destination')[1].get_x()-before[0])

    def test_every_step_uses_the_fit_needed_by_the_longest_later_equation(self):
        first=ListScene();first.add('equation',Equation({'x':'x'}))
        second=first.fork().revise('equation',{'x':'+'.join(map(str,range(1,25)))})
        group=SceneSequence('one calculation')
        group.add(first,reason='Name the value')
        group.add(second,reason='Expand the value')
        source_size=first.target('equation').font_size
        group.compile()
        a,b=[beat.scene for beat in group.beats]
        self.assertAlmostEqual(a.target('equation').font_size,b.target('equation').font_size)
        self.assertLess(a.target('equation').font_size,source_size)
        self.assertEqual(first.target('equation').font_size,source_size)
        self.assertEqual(a.layout_report()['layoutGroup'],'one calculation')

    def test_proof_rows_reserve_the_later_fraction_and_additional_lines(self):
        first=ProofSlide('Induction')
        first.add('claim',Equation({'call':'f(n)','eq':'=','value':'n'}))
        first.add('inductive_step',Equation({'call':'f(k+1)','eq':'=','value':'f(k)+k+1'}))
        second=first.fork().substitute('claim',value=r'\frac{n(n+1)}2')
        second=second.substitute('inductive_step',value=r'\frac{k(k+1)}2+k+1')
        second.add('induction_hypothesis','Assume the formula for k.')
        group=SceneSequence('complete proof')
        group.add(first,reason='Introduce the proof')
        group.add(second,reason='Use the closed form')
        group.compile()
        a,b=[beat.scene for beat in group.beats]
        self.assertNotIn('induction_hypothesis',a.items)
        for name in ('claim','inductive_step'):
            self.assertAlmostEqual(a.target(name).font_size,b.target(name).font_size)
            self.assertAlmostEqual(a.target(name).baseline,b.target(name).baseline)
        self.assertEqual(a.frame.rows,b.frame.rows)

    def test_unreadable_combined_scope_fails_before_any_scene_is_played(self):
        first=ListScene();first.add('note',TextObject('A supporting note.',type_role='note'))
        second=ListScene();second.add('diagram',Rectangle(width=17,height=1))
        group=SceneSequence('too much for one shared fit')
        group.add(first,reason='Introduce the note')
        group.add(second,reason='Show a large diagram')
        calls=[]
        renderer=SimpleNamespace(transition_to=lambda *args,**kwargs:calls.append(args))
        with self.assertRaisesRegex(ValueError,'too small'):group.play(renderer)
        self.assertEqual(calls,[])

    def test_played_groups_are_sealed_but_parent_can_add_a_new_explanation(self):
        film=LessonAnimation();group=film.group('first explanation')
        first=ListScene();first.add('text','One explanation')
        group.add(first,reason='Begin the explanation')
        calls=[]
        renderer=SimpleNamespace(transition_to=lambda *args,**kwargs:calls.append(args))
        film.play(renderer)
        with self.assertRaisesRegex(ValueError,'every step before playback'):
            group.add(first,reason='A late extra step')
        second=film.group('another explanation');second.add(first,reason='Begin another explanation')
        film.play(renderer)
        self.assertEqual(len(calls),2)

    def test_nested_groups_inherit_the_whole_explanations_fitting_contract(self):
        first=ListScene();first.add('equation',Equation({'value':'x'}))
        later=first.fork().revise('equation',{'value':'+'.join(map(str,range(1,25)))})
        group=SceneSequence('one derivation')
        group.add(first,reason='Name the value')
        nested=group.group('algebra');nested.add(later,reason='Expand it')
        group.compile()
        a=group.beats[0].scene;b=nested.beats[0].scene
        self.assertAlmostEqual(a.target('equation').font_size,b.target('equation').font_size)
        self.assertEqual(nested.layout_report,group.layout_report)
        self.assertTrue(nested._sealed)

    def test_wrapped_proof_rows_are_not_refitted_after_the_text_was_scaled(self):
        proof=ProofSlide('A proof')
        proof.add('definitions',Equation({'measure':'k=n-i+1'}))
        proof.add('claim','P(k): f gives the minimum weight for every target v when k items remain.')
        proof.add('base_case',MathStack(Equation({'a':'f(n+1,0)=0'}),Equation({'b':r'f(n+1,v)=\infty\quad(v>0)'})))
        proof.add('induction_hypothesis','Assume the minimum weight is correct when k−1 items remain.')
        proof.add('inductive_step','Every subset takes or skips item i. Its child has k−1 items. Add the immediate weight when taking, then choose the smaller feasible weight.')
        proof.validate()


if __name__=='__main__':unittest.main()
