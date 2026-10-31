import unittest
from unittest.mock import patch
from types import SimpleNamespace
from manim import Scene,Group,ImageMobject,Text
import numpy as np
from algovis import (CaseEquation, ColumnSlide, Equation, LessonAnimation, MathRow, ViewTransition,
                     CenteredScene,StateSequence,MathStack,SemanticProperties,DEFAULT_THEME)
from algovis import RecursiveTree,TreeScene
from tests.test_composition import start,finish
from tests.test_composition import apply


class SceneAnimationTests(unittest.TestCase):
    def test_renderer_remembers_an_applied_copy_when_the_same_view_gains_a_row(self):
        from algovis import ViewScene,ApplyDefinition,Pulse
        from manim import tempconfig
        first=CenteredScene();source=first.add('source',Equation({'call':'f(n)'}))
        first.add('cases',CaseEquation(Equation({'call':'f(n)'}),[Equation({'future':'0'})]))
        applied=first.fork().apply_definition('cases','row:0.future',source.part('call'),'f(n)')
        film=LessonAnimation();film.add(applied,reason='Apply the definition')
        with tempconfig({'dry_run':True,'disable_caching':True}):
            scene=ViewScene(skip_animations=True);scene.setup();scene.set_view(first)
            with patch('algovis.composition.ApplyDefinition.bind',wraps=ApplyDefinition.bind) as transfer:
                film.play(scene)
                scene.play(Pulse(source.mobject,trigger='definition',reason='Refer to the visible definition'),run_time=.1)
                applied.add('base','The base case')
                film.add(applied,reason='Add the base without replaying the completed copy')
                film.play(scene)
            self.assertEqual(transfer.call_count,1)
            self.assertIs(scene.current_view.definition_uses['cases'],film.beats[-1].scene.definition_uses['cases'])

    def test_definition_copy_can_use_the_clear_outer_motion_margin(self):
        from algovis import ListScene
        first=ListScene()
        first.add('meaning','Minimum weight for a target. Choose the largest feasible target value.')
        handle=first.add('all_items',Equation({'call':'f[1,v]','meaning':r'=\text{minimum weight to reach at least }v'}))
        first.add('bound',Equation({'total':r'V=\sum_{i=1}^n v_i','range':r'\qquad0\le v\le V'}))
        first.add('seek','find the largest target v')
        second=first.fork();second.add('feasible',Equation({'call':handle.part('call')}))
        first.install(Scene());handle.mobject.move_to(second.target('all_items'))
        source=handle.mobject.part('call');destination=second.target('feasible').part('call')
        via=second.definition_route(source,destination,vacant_destination=True)
        self.assertTrue(via)
        self.assertLess(via[0][0],source.get_left()[0])
        from manim import config
        self.assertGreater(via[0][0]-source.width/2,-config.frame_width/2+.18)
        third=second.fork()
        wrapper=third.add('answer',Equation({'max':r'\max\{v\mid 0\le v\le V,',
                                            'call':handle.part('call'),'end':r'\le C\}'}))
        handle.mobject.move_to(third.target('all_items'))
        wrapper.mobject.adopt_layout(third.target('answer'))
        destination=wrapper.mobject.part('call')
        via=third.definition_route(source,destination,vacant_destination=True)
        # An entering row uses its live owner after adoption. Its retained
        # prefix must not disappear from the landing-obstacle calculation.
        self.assertLess(via[-1][1],destination.get_bottom()[1])
        self.assertAlmostEqual(via[-1][0],destination.get_x())

    def test_new_equation_wrapper_waits_for_a_copy_using_its_empty_row(self):
        from algovis import ListScene
        first=ListScene()
        first.add('meaning','The minimum weight tells us which target values are feasible. '
                  'We seek the largest value whose required weight fits in the bag.')
        first.add('bound',Equation({'range':r'0\le v\le V'}))
        first.add('seek','Find the largest feasible target value.')
        handle=first.add('source',Equation({'call':'f[1,v]','condition':r'\le C'}))
        second=first.fork()
        result=second.add('answer',Equation({'max':r'\max\{v\mid 0\le v\le V,',
                                           'call':handle.part('call'),'end':r'\le C\}'}))
        stage=Scene();first.install(stage)
        # The compiler routes copies after preparing retained rows, so the
        # source is already in the incoming layout when its exit is measured.
        handle.mobject.move_to(second.target('source'))
        destination=second.target('answer').part('call')
        via=second.definition_route(handle.mobject.part('call'),destination,vacant_destination=True)
        self.assertTrue(via.vacant_destination)
        self.assertAlmostEqual(via[0][0],handle.mobject.part('call').get_x())
        self.assertAlmostEqual(via[0][1],destination.get_y())
        plan=ViewTransition(first,second)
        for animation in plan.animations(stage):
            start(animation,stage);animation.interpolate(.4)
            painted={id(part) for root in stage.mobjects for part in root.family_members_with_points()}
            self.assertFalse(painted & {id(part) for part in result.mobject.part('max').family_members_with_points()})
            finish(animation,stage)
        plan.commit(stage)
        self.assertIn(handle.mobject,stage.mobjects)
        self.assertEqual(result.mobject.native_layout_findings(),[])

    def test_a_case_definition_leaves_away_from_its_own_rhs_in_a_proof(self):
        from algovis import ProofSlide
        first=ProofSlide()
        recurrence=CaseEquation(Equation({'call':'f(i,w)','eq':r'=\max'}),[
            Equation({'take':'v_i+f(i+1,w+w_i)'}),Equation({'skip':'f(i+1,w)'})])
        base=CaseEquation(Equation({'call':'f(n,w)','eq':'='}),[
            Equation({'yes':r'v_n\quad\text{if }w+w_n\le C'}),Equation({'no':r'0\quad\text{otherwise}'})])
        handle=first.define_algorithm(recurrence,base)
        first.add('claim',Equation({'p':'P(k):','meaning':r'\text{all instances of size at most }k'}))
        second=first.fork();second.add('base_case',Equation({'call':handle.part('1.lhs.call')}))
        first.install(Scene())
        source=base.lhs.part('call');destination=second.target('base_case').part('call')
        route=second.definition_route(source,destination)
        self.assertTrue(route)
        self.assertLess(route[0][0],source.get_left()[0])
        self.assertAlmostEqual(route[0][1],source.get_y())

    def test_cases_wait_for_a_moving_condition_even_when_the_row_start_is_fixed(self):
        old=Equation({'words':r'\text{take item }i','condition':r'\text{if it fits}'})
        cases=CaseEquation(Equation({'f':r'f(i,w)=\max'}),[old])
        target=cases.with_state(rows=[old.next_layout(words=r'v_i+\text{best value after taking item }i')])
        stage=Scene();stage.add(cases)
        animation=cases.motions_to(target)[0]
        start(animation,stage);animation.interpolate(.55)
        painted={id(part) for root in stage.mobjects for part in root.family_members_with_points()}
        self.assertFalse(painted & {id(part) for part in target.rows[0].part('words').family_members_with_points()})
        finish(animation,stage)

    def test_case_lhs_copy_avoids_its_optimizer_and_other_alternatives(self):
        from algovis import RecurrenceScene
        first=RecurrenceScene()
        cases=CaseEquation(Equation({'call':'f(i,v)','opt':r'=\min'}),[
            Equation({'skip':'f(i+1,v)'}),Equation({'future':r'\text{minimum remaining weight}'})])
        handle=first.add('rule',cases,slot='equation')
        second=first.fork().apply_definition('rule','row:1.future',handle.part('lhs.call'),'f(i+1,v)')
        first.install(Scene())
        destination=second.target('rule').rows[1].part('future')
        route=second.definition_route(cases.lhs.part('call'),destination)
        self.assertEqual(len(route),2)
        self.assertLess(route[0][1],cases.get_bottom()[1])
        self.assertAlmostEqual(route[0][0],cases.lhs.part('call').get_x())
        self.assertAlmostEqual(route[-1][0],destination.get_x())

    def test_an_equation_applying_its_own_definition_leaves_above_the_words(self):
        from algovis import ListScene
        first=ListScene()
        row=Equation({'begin':r'\begin{aligned}','call':r'f(\text{state})','eq':'&=',
            'meaning':r'\text{best value for this instance}','line':r'\\','rhs':'&=',
            'future':r'\text{???}','end':r'\end{aligned}'})
        handle=first.add('rule',row)
        second=first.fork().substitute('rule',future=r'f(\text{state after }c)',from_definition=handle.part('call'))
        first.install(Scene())
        route=second.definition_route(row.part('call'),second.target('rule').part('future'))
        self.assertEqual(len(route),2)
        self.assertAlmostEqual(route[0][0],row.part('call').get_x())
        self.assertGreater(route[0][1],row.get_top()[1])

    def test_cases_retire_english_before_revealing_newly_named_recursive_terms(self):
        old=Equation({'words':r'\text{best value if we skip item }i'})
        cases=CaseEquation(Equation({'f':'f(i,w)=\\max'}),[old])
        target=cases.with_state(rows=[Equation({'f':'f(','i':'i+1','rest':',w)'})])
        stage=Scene();stage.add(cases)
        animation=cases.motions_to(target)[0]
        start(animation,stage);animation.interpolate(.15)
        painted={id(part) for root in stage.mobjects for part in root.family_members_with_points()}
        self.assertFalse(painted & {id(part) for part in target.rows[0].family_members_with_points()})
        animation.interpolate(.3)
        self.assertTrue(all(float(np.max(glyph.get_fill_opacity()))<.001
                            for glyph in old.family_members_with_points()))
        finish(animation,stage)

    def test_definition_replaces_english_before_neighbor_terms_use_its_space(self):
        from algovis import DerivationScene
        first=DerivationScene()
        row=Equation({'f':'f(x)=','immediate':r'\text{immediate effect}',
                      'plus':'+','future':r'\text{long-term effect}'})
        first.add('rule',row,slot='equation')
        source=first.add('distance',Equation({'call':'d(i,j)'}),slot='footer')
        second=first.fork().substitute('rule',immediate='d(i,j)',from_definition=source.part('call'))
        stage=Scene();first.install(stage)
        future=row.part('future').get_center().copy()
        plan=ViewTransition(first,second)
        for animation in plan.animations(stage):
            start(animation,stage);animation.interpolate(.15)
            np.testing.assert_allclose(row.part('future').get_center(),future)
            animation.interpolate(.25)
            self.assertTrue(all(float(np.max(glyph.get_fill_opacity()))<.001
                                for glyph in row.part('immediate').family_members_with_points()))
            finish(animation,stage)
        plan.commit(stage)
        self.assertEqual(row.slot_tex['immediate'],'d(i,j)')
        self.assertEqual(row.native_layout_findings(),[])
        self.assertIn(source.mobject,stage.mobjects)

    def test_delimiter_wrapped_words_are_prose_but_named_function_states_are_math(self):
        row=Equation({'open':r'\left(','words':r'\text{immediate effect}','close':r'\right)'})
        self.assertTrue(row.prose_term('words'))
        wrapped=Equation({'words':r'\bigl(\text{a choice}\bigr)'})
        self.assertTrue(wrapped.prose_term('words'))
        self.assertFalse(Equation({'call':r'f(\text{state})'}).prose_term('call'))

    def test_moving_native_equation_reveals_its_new_terms_only_after_arrival(self):
        row=Equation({'call':'f(x)'})
        target=row.next_layout({'call':'f(x)','label':r'\text{value}'}).shift([0,1,0])
        stage=Scene();stage.add(row)
        for animation in row.motions_to(target):
            start(animation,stage);animation.interpolate(.4)
            painted={id(part) for root in stage.mobjects for part in root.family_members_with_points()}
            self.assertNotIn(id(target.part('label')),painted)
            finish(animation,stage)
        row.commit(target,stage)
        self.assertEqual(row.slot_tex['label'],r'\text{value}')

    def test_moving_cases_coordinate_new_labels_across_all_nested_rows(self):
        row=Equation({'value':'x'})
        cases=CaseEquation(Equation({'call':'f(x)','eq':'='}),[row])
        target=cases.with_state(rows=[row.next_layout({'value':'x','label':r'\text{take}'})]).shift([0,1,0])
        stage=Scene();stage.add(cases)
        animations=cases.motions_to(target)
        self.assertEqual(len(animations),1)
        animation=animations[0];start(animation,stage);animation.interpolate(.4)
        painted={id(part) for root in stage.mobjects for part in root.family_members_with_points()}
        self.assertNotIn(id(target.rows[0].part('label')),painted)
        finish(animation,stage);cases.adopt_layout(target)
        self.assertIs(cases.rows[0],row)
        self.assertEqual(row.slot_tex['label'],r'\text{take}')

    def test_cases_reflow_waits_for_existing_rows_even_when_lhs_stays_put(self):
        row=Equation({'value':'x'})
        cases=CaseEquation(Equation({'call':'f(x)','eq':'='}),[row])
        target=cases.with_state(rows=[row,Equation({'value':'y'})])
        self.assertAlmostEqual(cases.lhs.get_y(),target.lhs.get_y())
        self.assertGreater(abs(cases.rows[0].get_y()-target.rows[0].get_y()),.1)
        stage=Scene();stage.add(cases)
        animation=cases.motions_to(target)[0]
        start(animation,stage);animation.interpolate(.4)
        painted={id(part) for root in stage.mobjects for part in root.family_members_with_points()}
        self.assertFalse(painted & {id(part) for part in target.rows[1].family_members_with_points()})
        finish(animation,stage)

    def test_changed_prose_appended_to_a_function_call_requires_named_terms(self):
        row=Equation({'property':r'f(i,w)\text{ is optimal whenever }n-i+1\le k'})
        target=row.next_layout(property=r'f(k,w)\text{ is optimal for every valid }w')
        with self.assertRaisesRegex(ValueError,'separate named math and prose'):
            row.motions_to(target)

    def test_prose_units_after_tex_space_do_not_morph_their_letters(self):
        from algovis.utils.effects import ReplaceContent
        row=Equation({'units':r'\ \text{unique states}'})
        motions=row.motions_to(row.next_layout(units=r'\ \text{states}'))
        self.assertTrue(any(isinstance(motion,ReplaceContent) for motion in motions))

    def test_new_case_equation_waits_for_the_retained_meaning_to_clear_its_space(self):
        from algovis import ComparisonScene,RecurrenceScene,TextObject
        first=ComparisonScene()
        meaning=first.add('meaning',TextObject('Minimum remaining weight'),slot='right')
        stage=Scene();first.install(stage)
        second=RecurrenceScene()
        second.add('meaning',meaning,slot='meaning')
        equation=second.add('recurrence',CaseEquation(Equation({'call':'f(i,v)','eq':'=','opt':r'\min'}),[
            Equation({'skip':r'\text{exclude item }i'})]),slot='equation')
        plan=ViewTransition(first,second)
        for animation in plan.animations(stage):
            start(animation,stage)
            animation.interpolate(.35)
            painted={id(part) for root in stage.mobjects for part in root.family_members_with_points()}
            self.assertFalse(painted & {id(part) for part in equation.mobject.family_members_with_points()})
            finish(animation,stage)
        plan.commit(stage)
        self.assertIn(equation.mobject,stage.mobjects)

    def test_state_parameter_is_a_math_refinement_even_when_its_label_uses_text(self):
        from manim import Transform
        from algovis.utils.effects import ReplaceContent
        row=Equation({'call':r'f(\ldots)'})
        target=row.next_layout(call=r'f(\text{state})')
        motions=row.motions_to(target)
        self.assertFalse(any(isinstance(motion,ReplaceContent) for motion in motions))
        self.assertTrue(any(isinstance(motion,Transform) and motion.mobject is row.part('call')
                            for motion in motions))

    def test_underbrace_annotation_preserves_the_named_operand_and_its_paint(self):
        row=Equation({'a':'a','plus':'+','b':'b'},roles={'a':'operation'})
        first=ColumnSlide();first.add('sum',row)
        second=first.fork().revise('sum',row.annotation_parts('a',r'\text{immediate}'))
        stage=Scene();first.install(stage);operand=row.part('a')
        apply(ViewTransition(first,second),stage)
        self.assertIs(row.part('a'),operand)
        self.assertEqual(row.part('a').get_color(),DEFAULT_THEME.accent)
        self.assertEqual(row.part('annotation:a:close').get_color(),DEFAULT_THEME.foreground)
        third=second.fork().revise('sum',row.annotation_parts('a'))
        apply(ViewTransition(second,third),stage)
        self.assertIs(row.part('a'),operand)
        self.assertNotIn('annotation:a:close',row.parts)
        self.assertEqual(row.native_layout_findings(),[])

    def test_equation_inside_a_layout_row_can_reveal_its_checkmark(self):
        from algovis import ObjectRow
        first=ColumnSlide();group=ObjectRow(Text('From here'),Equation({'mark':r'\phantom{\checkmark}'},status='computed'))
        first.add('heading',group)
        second=first.fork().refine('heading',index=1,parts={'mark':r'\checkmark'})
        stage=Scene();first.install(stage);mark=group[1]
        apply(ViewTransition(first,second),stage)
        self.assertIs(group[1],mark)
        self.assertEqual(mark.slot_tex['mark'],r'\checkmark')
        self.assertEqual(mark.part('mark').get_color(),DEFAULT_THEME.success)

    def test_rewording_a_caption_keeps_its_owner_without_morphing_letters(self):
        first=ColumnSlide();caption=first.add('label',Text('RECURSIVE FUNCTION'))
        second=first.fork().reword('label','DYNAMIC PROGRAMMING')
        stage=Scene();first.install(stage)
        transition=ViewTransition(first,second)
        apply(transition,stage)
        self.assertIs(second.object('label'),caption)
        self.assertEqual(caption.mobject._algovis_source_text,'DYNAMIC PROGRAMMING')
        self.assertEqual(stage.mobjects,[caption.mobject])

    def test_prose_term_replacement_does_not_prepaint_destination(self):
        first=ColumnSlide();row=Equation({'value':'f(n)','note':r'\quad(\text{exponential growth})'})
        first.add('bound',row)
        second=first.fork().substitute('bound',note=r'\in\Omega(1.6^n)')
        stage=Scene();first.install(stage)
        from algovis.utils.effects import ReplaceContent,DeferredAnimation
        replacement=next(a for a in row.motions_to(second.target('bound')) if isinstance(a,ReplaceContent))
        self.assertIsInstance(replacement.animations[1],DeferredAnimation)
        start(replacement,stage)
        future=second.target('bound').part('note')
        self.assertNotIn(future,stage.get_mobject_family_members())
        replacement.interpolate(.25)
        self.assertNotIn(future,stage.get_mobject_family_members())
        finish(replacement,stage)
        self.assertIn(future,stage.get_mobject_family_members())

    def test_spacing_changes_do_not_retire_unchanged_equation_words(self):
        from manim import Transform
        row=Equation({'prefix':r'\text{Suppose}'})
        target=row.next_layout({'prefix':r'\text{Suppose}\quad','value':'1.6^n'})
        motions=row.motions_to(target)
        self.assertTrue(any(isinstance(motion,Transform) and motion.mobject is row.part('prefix')
                            for motion in motions))

    def test_addition_operator_is_replaced_in_the_gap_instead_of_crossing_values(self):
        from algovis.utils.effects import ReplaceContent
        sequence=StateSequence([1,1,2,''])
        stage=Scene();stage.add(sequence)
        guide=sequence.begin_addition();start(guide,stage);finish(guide,stage)
        old=sequence._plus
        step=sequence.add_next(3,3)
        replacement=next(a for a in step.animations if isinstance(a,ReplaceContent) and a.animations[0].mobject is old)
        start(step,stage);step.interpolate(.25)
        self.assertNotIn(sequence._plus,stage.get_mobject_family_members())
        finish(step,stage)
        expected=(sequence.row[1].get_right()+sequence.row[2].get_left())/2
        np.testing.assert_allclose(sequence._plus.get_center(),expected)
        self.assertEqual(sequence.cell(3).label.tex_string,'3')

    def test_arriving_in_a_new_city_clears_the_previous_purchase(self):
        from algovis import RoadTripSimulation
        trip=RoadTripSimulation(capacity=2,prices=[4,2,5],consumption=[1,1,1])
        stage=Scene();stage.add(trip)
        for action in (trip.start,lambda:trip.buy(1),trip.drive):
            animation=action();start(animation,stage);finish(animation,stage)
        self.assertEqual(trip.city,1)
        self.assertEqual(trip.fuel,0)
        self.assertEqual(trip.costs,[4])
        self.assertEqual(trip.purchase.slot_tex['b'],r'\text{buy: }0')

    def test_storage_brace_survives_compiled_checklist_reveals(self):
        from algovis import Checklist
        checklist=Checklist(['One','Two','Three','Four','Store'])
        first=ColumnSlide();first.add('list',checklist)
        last=first.fork().refine('list',visible=5,recursion_brace=True,dp_brace=True)
        stage=Scene();apply(ViewTransition(None,first),stage);apply(ViewTransition(first,last),stage)
        self.assertTrue(checklist.dp_brace)
        self.assertGreater(checklist.storage_label.get_fill_opacity(),.9)
        self.assertLess(checklist.storage_brace.get_top()[1],checklist.brace.get_bottom()[1])

    def test_component_reference_keeps_its_planned_base_case_before_playback(self):
        base=CaseEquation(Equation({'call':'f(n,w)','eq':'='}),[Equation({'answer':'v_n'})])
        proof=ColumnSlide();proof.add('definitions',MathStack(base))
        future=proof.fork().refine('definitions',rows=[
            CaseEquation(Equation({'call':'f(n+1,w)','eq':'='}),[Equation({'answer':'0'})])])
        answer=ColumnSlide();answer.add('base',future.part('definitions','0'))
        self.assertEqual(answer.target('base').lhs.slot_tex['call'],'f(n+1,w)')
        self.assertEqual(answer.target('base').rows[0].slot_tex['answer'],'0')
        self.assertEqual(base.lhs.slot_tex['call'],'f(n,w)')

    def test_semantics_address_the_actual_term_inside_nested_definition_containers(self):
        view=ColumnSlide()
        view.add('definition',MathStack(Equation({'f':'f(','child':'i+1','close':',w)'})))
        known=view.fork().set_meaning('definition',part='0.child',status='known')
        self.assertEqual(known.target('definition')[0].part('child').semantics.status,'known')
        self.assertNotEqual(known.target('definition')[0].part('child').get_color(),
                            view.target('definition')[0].part('child').get_color())

    def test_tree_continuation_stays_unboxed_through_its_reveal(self):
        tree=RecursiveTree(lambda n:(n,[(r'\vdots',)] if n=='n' else []),('n',),
                           profile='compact',reveal_depth=0)
        animation=tree.get_depth_reveal_anim(1)
        animation.begin()
        for alpha in (.25,.5,1):
            animation.interpolate(alpha)
            dots=tree.tree_structure['children'][0]['mobject']
            self.assertEqual(float(np.max(dots.box.get_fill_opacity())),0)
            self.assertEqual(float(np.max(dots.box.get_stroke_opacity())),0)
        animation.finish()
        self.assertGreater(dots.label.get_fill_opacity(),.9)

    def test_algorithm_proof_requires_the_recursive_definition_not_its_claim(self):
        from algovis import ProofSlide,TextObject
        proof=ProofSlide()
        with self.assertRaisesRegex(TypeError,'not a prose correctness claim'):
            proof.define_algorithm(TextObject('f is the optimum'),Equation({'base':'f(0)=0'}))
        recurrence=Equation({'call':'f(n)','eq':'=','child':'f(n-1)+n'})
        base=Equation({'base':'f(0)=0'})
        proof.define_algorithm(recurrence,base)
        self.assertIs(proof.object('definitions').mobject[0],recurrence)
        self.assertIs(proof.object('definitions').mobject[1],base)
        with self.assertRaisesRegex(TypeError,'intended meaning belongs in the claim'):
            proof.fork().refine('definitions',rows=[TextObject('f is the optimum'),base])

    def test_named_math_span_reuses_its_terms_without_owning_new_glyphs(self):
        row=Equation({'now':'v_i+','future_open':'f(','future_index':'i+1',
                      'future_rest':',w)','condition':r'\quad w+w_i\le C'})
        selected=row.part('future*')
        self.assertEqual(selected.tex_string,'f(i+1,w)')
        self.assertIs(selected[1],row.part('future_index'))
        self.assertNotIn(row.part('condition'),selected.submobjects)
        changed=row.next_layout(future_index='i+2')
        self.assertEqual(changed.part('future*').tex_string,'f(i+2,w)')

    def test_bag_attempt_is_separate_from_its_valid_load_and_returns(self):
        import tempfile
        from pathlib import Path
        from PIL import Image
        from algovis import IllustratedBag,SlideObject
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'prop.png';Image.new('RGBA',(40,60),'white').save(path)
            bag=IllustratedBag(path).with_state(capacity=6,used=5,show_meter=True)
            item=SlideObject(ImageMobject(np.full((8,8,4),255,dtype=np.uint8)))
            attempt=bag.with_state(attempt=item)
            rejected=attempt.with_state(reject_attempt=True)
            returned=rejected.with_state(return_attempt=True)
            self.assertEqual([x.meter.used for x in (bag,attempt,rejected,returned)],[5]*4)
            self.assertIsNotNone(rejected.rejection)
            self.assertIsNone(returned.attempt)
            self.assertIsNone(returned.rejection)
            scene=Scene();view=ColumnSlide();view.add('bag',bag);view.add('item',item);view.install(scene)
            pending=view.fork().refine('bag',attempt=item)
            apply(ViewTransition(view,pending),scene)
            rejected=pending.fork().refine('bag',reject_attempt=True)
            apply(ViewTransition(pending,rejected),scene)
            returned=rejected.fork().refine('bag',return_attempt=True)
            apply(ViewTransition(rejected,returned),scene)
            self.assertIsNone(bag.attempt)
            self.assertEqual(len(bag.contents),0)
            self.assertEqual(bag.meter.used,5)

    def test_card_natural_geometry_does_not_inherit_a_previous_scene_scale(self):
        from algovis import IllustratedItem
        from algovis.layout import LessonTypography
        card=IllustratedItem(np.full((12,16,4),255,dtype=np.uint8),'item',1,
                             metric_reserve={'weight':3,'value':10})
        card.scale(.65)
        card.apply_scene_typography(LessonTypography(),group='cards')
        self.assertAlmostEqual(card.frame.width,2.3)
        self.assertAlmostEqual(card.frame.height,2.25)
        updated=card.with_state(weight=3,value=10)
        updated.apply_scene_typography(LessonTypography(),group='cards')
        self.assertAlmostEqual(updated.frame.width,card.frame.width)
        self.assertAlmostEqual(updated.frame.height,card.frame.height)

    def test_component_reveals_survive_the_entire_lesson_timeline(self):
        from algovis import Checklist,PseudocodePanel,RecapScene
        for component,states in [(Checklist(['First','Second']),[{'visible':1},{'visible':2},{'recursion_brace':True}]),
                (PseudocodePanel(['array','function','check','store']).with_state(visible_lines=(1,)),
                 [{'visible_lines':(0,1)},{'visible_lines':(0,1,2)},{'visible_lines':(0,1,2,3)}])]:
            view=ColumnSlide();handle=view.add('component',component)
            film=LessonAnimation();group=film.group('Retain declared component reveals')
            group.add(view,reason='Introduce the component')
            for state in states:
                view=view.fork().refine('component',**state);group.add(view,reason='Reveal the specified content')
            scene=Scene();current=None
            def transition(view,**options):
                nonlocal current
                apply(ViewTransition(current,view),scene);current=view
            film.play(SimpleNamespace(transition_to=transition))
            if isinstance(component,Checklist):
                self.assertEqual(component.visible,2)
                self.assertTrue(component.recursion_brace)
                self.assertTrue(all(row.get_fill_opacity()>.9 for row in component.rows))
                self.assertGreater(component.brace_label.get_fill_opacity(),.9)
            else:
                self.assertTrue(all(line.get_fill_opacity()>.9 for line in component.lines))

    def test_refinement_rejects_undeclared_component_visibility_state(self):
        class Undeclared(Text):
            def with_state(self,*,visible):return self.copy().set_opacity(int(visible))
        view=ColumnSlide();view.add('component',Undeclared('Do not discard this reveal'))
        with self.assertRaisesRegex(ValueError,'declared content model'):
            view.fork().refine('component',visible=False)

    def test_code_reveal_keeps_its_opaque_background_and_text_in_one_owner(self):
        from algovis import PseudocodePanel
        panel=PseudocodePanel(['array','def f(state):','return answer']).with_state(visible_lines=(1,2))
        target=panel.with_state(visible_lines=(0,1,2))
        motions=panel.motions_to(target)
        self.assertEqual(len(motions),1)
        self.assertIs(motions[0].mobject,panel)
        self.assertLess(panel.submobjects.index(panel.background),panel.submobjects.index(panel.lines))

    def test_proof_substitution_prepares_suffix_and_routes_below_its_baseline(self):
        from algovis import ProofSlide
        proof=ProofSlide(profile='worked')
        proof.add('definitions',Equation({'definition':'f(n)=f(n-1)+n'}))
        proof.add('claim',Equation({'claim':r'P(n):f(n)=1+2+\cdots+n'}))
        proof.add('base_case',Equation({'base':'f(0)=0'}))
        hypothesis=proof.add('induction_hypothesis',Equation({'hypothesis':r'f(k)=','sum':r'1+2+\cdots+k'}))
        proof.add('inductive_step',Equation({'call':'f(k+1)','eq':'=','child':'f(k)','plus':'+','next':'(k+1)'}))
        proof.add('work',Equation({'eq':'=','child':'f(k)','plus':'+','next':'(k+1)'}))
        scene=Scene();proof.install(scene)
        target=proof.fork().substitute('work',from_definition=hypothesis.part('sum'),child=r'1+2+\cdots+k')
        row=target.target('work');via=target.definition_route(hypothesis.part('sum').mobject,row.part('child'))
        self.assertEqual(len(via),3)
        self.assertLess(via[-1][1]+row.part('child').height/2,row.part('next').get_bottom()[1])
        from algovis import ApplyDefinition
        with patch('algovis.composition.ApplyDefinition.bind',wraps=ApplyDefinition.bind) as transfer:
            apply(ViewTransition(proof,target),scene)
            self.assertEqual(transfer.call_count,1)
            self.assertTrue(np.allclose(proof.object('work').mobject.part('next').get_center(),row.part('next').get_center()))

    def test_fitted_cards_keep_their_geometry_during_other_cards_metric_updates(self):
        from algovis import IllustratedItem,ItemCollection,SelectionScene
        cards=[IllustratedItem(np.full((12,16,4),255,dtype=np.uint8),'item',i+1,
            metric_reserve={'weight':1,'value':10}) for i in range(6)]
        view=SelectionScene();view.add('items',ItemCollection(*cards,columns=6),slot='items')
        film=LessonAnimation();group=film.group('Populate the same fitted cards')
        group.add(view,reason='Introduce the cards')
        for i in range(6):
            view=view.fork().refine('items',index=i,weight=1,value=10)
            group.add(view,reason='Populate only the named card')
        group.compile();initial=group.beats[0].scene
        self.assertLess(initial.items['items'].fit_scale,1)
        expected=[card.frame.height for card in initial.target('items').cards]
        scene=Scene();current=None
        def transition(view,**options):
            nonlocal current
            apply(ViewTransition(current,view),scene);current=view
            for index,card in enumerate(cards):
                self.assertAlmostEqual(card.frame.height,expected[index])
                for metric in (card.weight,card.value):
                    self.assertGreater(metric.get_bottom()[1],card.frame.get_bottom()[1]+.02)
        film.play(SimpleNamespace(transition_to=transition))

    def test_contiguous_definition_terms_share_one_copy_route_and_keep_their_identities(self):
        from algovis import ProofSlide,ApplyDefinition
        proof=ProofSlide(profile='worked')
        source=proof.add('definitions',Equation({'call':'f(n)','eq':'=','child':'f(n-1)','plus':'+','n':'n'}))
        proof.add('claim',Equation({'p':r'P(n):f(n)=1+2+\cdots+n'}))
        proof.add('base_case',Equation({'b':'f(0)=0'}))
        step=proof.add('inductive_step',Equation({'call':'f(k+1)'}))
        scene=Scene();proof.install(scene)
        next_proof=proof.fork().revise('inductive_step',{'call':'f(k+1)','eq':'=',
            'child':source.part('child'),'plus':source.part('plus'),'n':source.part('n')})
        with patch('algovis.composition.ApplyDefinition.bind',wraps=ApplyDefinition.bind) as transfer:
            apply(ViewTransition(proof,next_proof),scene)
            self.assertEqual(transfer.call_count,1)
            self.assertEqual(len(transfer.call_args.args[0]),3)
            self.assertEqual(len(transfer.call_args.kwargs['via']),2)
        self.assertEqual(step.mobject.slot_tex['child'],'f(n-1)')
        self.assertIs(source.mobject.part('child'),proof.object('definitions').mobject.part('child'))

    def test_intrinsic_state_survives_regrouping_and_later_caption_only_beats(self):
        from algovis import ObjectRow,PairedScene
        from algovis.review.inspection import visible_opacity
        tree=RecursiveTree(lambda n:(str(n),[(n-1,)] if n else []),(3,),profile='compact',reveal_depth=0)
        first=PairedScene(pairs=(('step','trees'),))
        first.add('step','Choose a smaller input',slot='left')
        first.add('trees',ObjectRow(tree),slot='right')
        second=first.fork().remove('trees')
        second.add('trees',ObjectRow(tree),slot='right')
        third=second.fork().remove('step');third.add('step','Assume that smaller answer is correct',slot='left')
        fourth=third.fork().remove('step');fourth.add('step','Use that answer without revealing later descendants',slot='left')
        scene=Scene();current=None
        def transition(view,**options):
            nonlocal current
            apply(ViewTransition(current,view),scene);current=view
        def intrinsic(operation,**options):
            start(operation,scene);finish(operation,scene)
        renderer=SimpleNamespace(transition_to=transition,open_view=intrinsic)
        film=LessonAnimation();group=film.group('A partially revealed tree')
        group.add(first,reason='Show the parent')
        child=tree.tree_structure['children'][0]
        group.action(lambda:tree.get_node_reveal_anim(child),reason='Show only one child')
        from algovis import SemanticChange
        group.action(lambda:SemanticChange(child['mobject'],status='known'),reason='Assume the child answer is correct')
        group.add(second,reason='Regroup without changing revealed nodes')
        group.add(third,reason='Explain the assumed child answer')
        group.add(fourth,reason='Keep the same partially revealed tree')
        film.play(renderer)
        for data,depth in tree.iter_nodes():
            if depth<=1:self.assertGreater(visible_opacity(data['label']),.9)
            else:self.assertLess(visible_opacity(data['label']),.01)
        self.assertEqual(child['mobject'].semantics.status,'known')

    def test_regrouping_a_partially_drawn_tree_preserves_hidden_descendants(self):
        from algovis import ObjectRow,PairedScene,ViewScene
        from algovis.review.inspection import visible_opacity
        one=RecursiveTree(lambda n:(str(n),[(n-1,)] if n else []),(3,),profile='compact',reveal_depth=0)
        halves=RecursiveTree(lambda n:(str(n),[(n-1,),(n-1,)] if n else []),(2,),profile='compact',reveal_depth=0)
        first=PairedScene(pairs=(('step','trees'),))
        first.add('step','Choose smaller inputs',slot='left');first.add('trees',ObjectRow(one),slot='right')
        second=first.fork().remove('trees');second.add('trees',ObjectRow(one,halves),slot='right')
        film=LessonAnimation();group=film.group('Tree alternatives')
        group.add(first,reason='First alternative')
        group.add(second,reason='Second alternative shares the same first tree')
        group.compile();a,b=[beat.scene for beat in group.beats]
        scene=ViewScene();scene.setup();apply(ViewTransition(None,a),scene)
        animation=one.get_node_reveal_anim(one.tree_structure['children'][0]);start(animation,scene);finish(animation,scene)
        b.retain_live_models(a);apply(ViewTransition(a,b),scene)
        for data,depth in one.iter_nodes():
            self.assertGreater(visible_opacity(data['label']),.9) if depth<=1 else self.assertLess(visible_opacity(data['label']),.01)
        for data,depth in halves.iter_nodes():
            self.assertGreater(visible_opacity(data['label']),.9) if depth==0 else self.assertLess(visible_opacity(data['label']),.01)

    def test_domino_motion_reserves_its_height_and_animates_complete_labeled_cells(self):
        from algovis import InductionChain
        chain=InductionChain(3,known=(0,1,2),dominoes=True)
        first=CenteredScene();first.add('implication',Equation({'p':r'P(k)\Longrightarrow P(k+1)'}));first.add('cases',chain)
        scene=Scene();first.install(scene)
        caption=first.object('implication').mobject
        animation=chain.as_dominoes()
        self.assertFalse(any(child.mobject is case.box or child.mobject is case.label for child in animation.animations for case in chain.cases))
        start(animation,scene)
        for alpha in (.25,.5,.75,1):
            animation.interpolate(alpha)
            for case in chain.cases:self.assertLess(case.box.get_top()[1],caption.get_bottom()[1]-.1)
        finish(animation,scene)
        for case in chain.cases:
            self.assertEqual(case.box.get_stroke_color(),chain.theme.success)
            np.testing.assert_allclose(case.label.get_center(),case.box.get_center(),atol=1e-7)

    def test_induction_status_fill_survives_the_domino_morph_and_fall(self):
        from algovis import InductionChain
        chain=InductionChain(3,known=(0,1,2),dominoes=True)
        scene=Scene();scene.add(chain)
        colors=[case.box.get_fill_color() for case in chain.cases]
        morph=chain.as_dominoes();start(morph,scene);finish(morph,scene)
        for case,color in zip(chain.cases,colors):
            self.assertEqual(case.box.get_fill_color(),color)
            self.assertEqual(case.label.get_color(),chain.theme.foreground)
        motion=chain.fall(0);start(motion,scene)
        for alpha in (.25,.5,.75,1):
            motion.interpolate(alpha)
            for case,color in zip(chain.cases,colors):
                self.assertEqual(case.box.get_fill_color(),color)
                self.assertEqual(case.label.get_color(),chain.theme.foreground)
        finish(motion,scene)

    def test_every_case_in_a_plural_propagation_visibly_pulses_and_becomes_known(self):
        from algovis import InductionChain
        from dataclasses import replace
        chain=InductionChain(4,theme=replace(DEFAULT_THEME,success='#55CC88'));scene=Scene();scene.add(chain)
        widths=[case.width for case in chain.cases]
        centers=[case.get_center().copy() for case in chain.cases]
        animation=chain.propagate((0,1,2,3),trigger='in every case',reason='Propagate the implication')
        start(animation,scene)
        for index in range(4):
            animation.interpolate((index+.5)/4)
            self.assertGreater(chain.cases[index].width,widths[index]*1.1)
        finish(animation,scene)
        for index,case in enumerate(chain.cases):
            self.assertAlmostEqual(case.width,widths[index])
            np.testing.assert_allclose(case.get_center(),centers[index])
            self.assertEqual(case.semantics.status,'computed')
        self.assertEqual(animation._algovis_attention['trigger'],'in every case')

    def test_vertical_tree_edges_meet_the_frame_centers_before_and_after_reveal(self):
        from algovis import ViewScene
        tree=RecursiveTree(lambda n:(str(n),[(n-1,)] if n else []),(2,),profile='compact',reveal_depth=0)
        scene=ViewScene();scene.setup();view=TreeScene();view.add('tree',tree,slot='diagram');view.install(scene)
        for parent,_ in tree.iter_nodes():
            for child in parent['children']:
                animation=tree.get_node_reveal_anim(child);start(animation,scene);finish(animation,scene)
        for data,_ in tree.iter_nodes():
            for child,edge in zip(data['children'],data['edges']):
                self.assertAlmostEqual(edge.get_start()[0],data['shape'].get_x())
                self.assertAlmostEqual(edge.get_end()[0],child['shape'].get_x())
                self.assertAlmostEqual(edge.get_start()[1],data['shape'].get_bottom()[1])
                self.assertAlmostEqual(edge.get_end()[1],child['shape'].get_top()[1])

    def test_generalized_sequence_retains_its_values_and_ends_at_a_symbolic_state(self):
        first=CenteredScene();sequence=StateSequence(['1','1','2'],indices=True,known=True)
        first.add('sequence',sequence)
        last=first.fork().refine('sequence',continuation=True,final_index='n')
        scene=Scene();first.install(scene);apply(ViewTransition(first,last),scene)
        self.assertEqual([cell.label.tex_string for cell in sequence.row],['1','1','2'])
        self.assertEqual(sequence.terminal.label.tex_string,'f[n]')
        self.assertGreater(sequence.terminal.get_left()[0],sequence.ellipsis.get_right()[0])
        self.assertEqual(sequence.terminal.semantics.status,'computed')

    def test_adding_a_row_to_the_same_view_does_not_replay_its_definition_use(self):
        from algovis import ApplyDefinition
        first=CenteredScene();source=first.add('source',Equation({'call':'f(n)'}))
        first.add('cases',CaseEquation(Equation({'call':'f(n)'}),[Equation({'future':'0'})]))
        applied=first.fork().apply_definition('cases','row:0.future',source.part('call'),'f(n)')
        second=applied.snapshot()
        applied.add('base',Text('The base case'))
        third=applied.snapshot()
        scene=Scene();first.install(scene)
        with patch('algovis.composition.ApplyDefinition.bind',wraps=ApplyDefinition.bind) as transfer:
            apply(ViewTransition(first,second),scene)
            self.assertEqual(transfer.call_count,1)
            apply(ViewTransition(second,third),scene)
            self.assertEqual(transfer.call_count,1)

    def test_new_label_waits_until_retained_text_has_cleared_its_space(self):
        first=CenteredScene();retained=first.add('retained',Text('Keep this equation'))
        second=first.fork();label=second.add('new',Text('Then explain it'))
        second.add('last',Text('And retain the result'))
        scene=Scene();first.install(scene)
        plan=ViewTransition(first,second)
        animation=plan.animations(scene)[0];start(animation,scene)
        animation.interpolate(.4)
        self.assertNotIn(id(label.mobject),{id(p) for p in scene.get_mobject_family_members()})
        finish(animation,scene);plan.commit(scene)
        self.assertIn(id(retained.mobject),{id(p) for p in scene.get_mobject_family_members()})
        self.assertIn(id(label.mobject),{id(p) for p in scene.get_mobject_family_members()})
        self.assertGreater(label.mobject.get_fill_opacity(),.9)

    def test_frame_fill_attention_never_paints_over_its_label_in_encoded_artwork(self):
        from algovis import StateCell,ViewScene
        from algovis.attention import WordAttention
        scene=ViewScene();scene.setup();cell=StateCell('8');scene.add(cell)
        scene.narration=SimpleNamespace(cues={'eight':SimpleNamespace(phrase='eight')})
        effect=WordAttention(cell,'eight',style='fill',reason='Name this stored value').animation(scene)
        scene.narration=None
        def ink():
            scene.camera.reset();scene.camera.capture_mobjects(scene.mobjects)
            return int(np.all(scene.camera.pixel_array[:,:,:3]>180,axis=2).sum())
        before=ink();self.assertGreater(before,20)
        animation=scene._compile_view(effect);start(animation,scene)
        for alpha in (0,.5,1):
            animation.interpolate(alpha);self.assertGreaterEqual(ink(),before*.9)
        finish(animation,scene);self.assertGreaterEqual(ink(),before*.9)

    def test_illustrated_selection_copies_only_each_new_item_and_retains_prior_contents(self):
        from algovis import IllustratedBag,IllustratedItem,ItemCollection,SelectionScene,SlideObject,ApplyDefinition
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from PIL import Image
        with TemporaryDirectory() as folder:
            path=Path(folder)/'prop.png'
            Image.fromarray(np.full((32,32,4),255,dtype=np.uint8)).save(path)
            item=IllustratedItem(path,'item',1,metric_reserve={'weight':1,'value':10})
            first=SelectionScene();first.add('items',ItemCollection(item),slot='items')
            bag=first.add('bag',IllustratedBag(path),slot='bag')
            first=first.refine('bag',capacity=6,show_meter=True)
            second=first.fork().refine('bag',used=1,store=SlideObject(item.image))
            third=second.fork().refine('bag',used=2)
            scene=Scene();first.install(scene)
            with patch('algovis.composition.ApplyDefinition.bind',wraps=ApplyDefinition.bind) as transfer:
                apply(ViewTransition(first,second),scene)
                self.assertEqual(transfer.call_count,1)
                self.assertEqual(len(bag.mobject.contents),1)
                apply(ViewTransition(second,third),scene)
                self.assertEqual(transfer.call_count,1)
                self.assertEqual(len(bag.mobject.contents),1)
                self.assertEqual(bag.mobject.meter.used,2)
            source_family={id(p) for p in item.image.get_family()}
            self.assertFalse(source_family & {id(p) for p in bag.mobject.contents.get_family()})
            initial=first.target('items').cards[0]
            changed=first.fork().refine('items',index=0,weight=1,value=10).target('items').cards[0]
            for key in ('weight','value'):
                self.assertAlmostEqual(getattr(initial,key).baseline,getattr(changed,key).baseline)
                self.assertAlmostEqual(getattr(initial,key).get_left()[0],getattr(changed,key).get_left()[0])

    def test_new_layout_container_reuses_its_children_and_reveals_its_new_brace_and_label(self):
        from algovis import BracedGroup
        first=CenteredScene();row=first.add('definition',Equation({'f':'f(n)=n'}))
        second=CenteredScene();group=BracedGroup(row.mobject,label='One definition')
        second.add('definitions',group)
        scene=Scene();first.install(scene);apply(ViewTransition(first,second),scene)
        family={id(part) for part in scene.get_mobject_family_members()}
        self.assertIn(id(row.mobject),family)
        self.assertIn(id(group.heading),family);self.assertIn(id(group.brace),family)

    def test_layout_refinement_cannot_silently_drop_an_unowned_child(self):
        first=CenteredScene();stack=first.add('rows',MathStack(Equation({'a':'a'})))
        second=first.fork().refine('rows',rows=[Equation({'a':'a'}),Equation({'b':'b'})])
        with self.assertRaisesRegex(ValueError,'child identities'):ViewTransition(first,second)

    def test_symbolic_child_labels_fit_the_compact_node_at_exact_padding(self):
        tree=RecursiveTree(lambda n:(n,[('n-1',)] if n=='n' else []),('n',),profile='compact',depth_limit=1)
        for node,_ in tree.iter_nodes():
            self.assertLessEqual(node['label'].width,node['shape'].width-.16+1e-7)

    def test_capacity_meter_keeps_used_load_and_readable_capacity_in_the_same_component(self):
        from algovis import CapacityMeter,SelectionScene
        from algovis.review.inspection import visible_opacity
        meter=CapacityMeter()
        view=SelectionScene();view.add('meter',meter,slot='bag')
        defined=view.fork().refine('meter',capacity=6,visible=True)
        selected=defined.fork().refine('meter',used=5)
        scene=Scene();view.install(scene)
        apply(ViewTransition(view,defined),scene);apply(ViewTransition(defined,selected),scene)
        self.assertEqual(meter.readout.slot_tex,{'used':'5','slash':'/','capacity':'6'})
        self.assertGreater(visible_opacity(meter.readout),.9)
        self.assertGreater(meter.fill.height,1)
        with self.assertRaisesRegex(ValueError,'must fit'):meter.with_state(used=8)

    def test_leaf_counter_does_not_prepaint_the_later_count_labels(self):
        from algovis import ViewScene
        def branch(n):return f'f({n})',[] if n<=2 else [(n-1,),(n-2,)]
        tree=RecursiveTree(branch,(4,),profile='compact').with_state(leaf_counts=True)
        scene=ViewScene();scene.setup();scene.add(tree)
        counting=scene._compile_view(tree.count_leaves())
        self.assertTrue(all(label.get_fill_opacity()==0 for label in tree.leaf_numbers))
        start(counting,scene);counting.interpolate(.12)
        self.assertTrue(all(label.get_fill_opacity()==0 for label in tree.leaf_numbers[1:]))
        finish(counting,scene)
        self.assertTrue(all(label.get_fill_opacity()>.9 for label in tree.leaf_numbers))

    def test_function_indices_do_not_introduce_array_brackets(self):
        sequence=StateSequence([1,1,2],indices=True,index_notation='function')
        self.assertEqual([label.tex_string for label in sequence.index_labels],['f(1)','f(2)','f(3)'])

    def test_folding_call_names_travel_beside_values_then_into_array_indices(self):
        from algovis import ViewScene
        def branch(n):return f'f({n})',[] if n<=2 else [(n-1,),(n-2,)]
        tree=RecursiveTree(branch,(4,),profile='compact',backbone_space=True)
        sequence=StateSequence([1,1,2,3],indices=True)
        sequence.shift([0,-4,0])
        scene=ViewScene();scene.setup();scene.add(tree,sequence)
        animation=scene._compile_view(tree.fold_to_backbone({(1,):1,(2,):1,(3,):2,(4,):3},keep_call_labels=True))
        start(animation,scene)
        for alpha in np.linspace(0,1,201):animation.interpolate(alpha)
        finish(animation,scene)
        self.assertEqual(len(tree.fold_labels),4)
        for node in tree.backbone():
            tag=tree.fold_labels[tree.fold_label_keys.index(tuple(node['args']))]
            self.assertGreater(tag.get_left()[0],node['mobject'].box.get_right()[0])
            self.assertNotEqual(tag.tex_string,node['mobject'].label.tex_string)
        animation=scene._compile_view(tree.merge_backbone_into(sequence))
        start(animation,scene)
        for alpha in np.linspace(0,1,61):animation.interpolate(alpha)
        finish(animation,scene)
        self.assertTrue(all(label.get_fill_opacity()==0 for label in tree.fold_labels))
        from algovis.review.inspection import visible_opacity
        self.assertTrue(all(visible_opacity(cell.label)>.9 for cell in sequence.row))

    def test_a_completed_transfer_is_not_repeated_when_the_equation_is_reused(self):
        from algovis import BlockScene
        first=ColumnSlide();source=first.add('definition',Equation({'f':'f(n)'}))
        second=first.fork();answer=second.add('answer',Equation({'f':source.part('f')}))
        scene=Scene();first.install(scene);apply(ViewTransition(first,second),scene)
        third=BlockScene();third.add('answer',answer)
        self.assertEqual(third.target('answer')._copy_sources,{})
        apply(ViewTransition(second,third),scene)
        fourth=third.fork();fourth.add('explanation','Keep the already-arrived value.')
        apply(ViewTransition(third,fourth),scene)

    def test_road_trip_dashboard_updates_fuel_on_purchase_and_drive(self):
        from algovis import RoadTripSimulation,ViewScene
        trip=RoadTripSimulation(capacity=2,prices=[4,2],consumption=[1,1])
        scene=ViewScene();scene.setup();scene.add(trip)
        operation=trip.buy(2)
        self.assertEqual(trip.state.slot_tex['fuel'],'0')
        animation=scene._compile_view(operation)
        start(animation,scene);finish(animation,scene)
        self.assertEqual(trip.state.slot_tex['city'],'1')
        self.assertEqual(trip.state.slot_tex['fuel'],'2')
        animation=scene._compile_view(trip.drive())
        start(animation,scene);finish(animation,scene)
        self.assertEqual(trip.state.slot_tex['city'],'2')
        self.assertEqual(trip.state.slot_tex['fuel'],'1')

    def test_folded_duplicate_values_stay_hidden_after_canonical_cells_move(self):
        from algovis import RecursiveTree,ViewScene
        def branch(n):return f'f({n})',[] if n<=2 else [(n-1,),(n-2,)]
        tree=RecursiveTree(branch,(5,),profile='compact',state_key=lambda args:args[0])
        scene=ViewScene();scene.setup();scene.add(tree)
        kept=tree.backbone();kept_ids={id(n['mobject']) for n in kept}
        animation=scene._compile_view(tree.fold_to_backbone({1:1,2:1,3:2,4:3,5:5}))
        start(animation,scene)
        for alpha in np.linspace(0,1,161):animation.interpolate(alpha)
        finish(animation,scene)
        for node,_ in tree.iter_nodes():
            if id(node['mobject']) in kept_ids:continue
            for glyph in node['mobject'].label.family_members_with_points():
                self.assertLessEqual(float(np.max(glyph.get_fill_opacity())),.001)
        # Revealing the old landing positions by moving the survivors must
        # leave no discarded values behind, even after compiler cleanup.
        for node in kept:node['mobject'].shift([0,-2,0])
        for root in scene.mobjects:
            if id(root) in {id(n['mobject']) for n,_ in tree.iter_nodes() if id(n['mobject']) not in kept_ids}:
                self.assertTrue(all(float(np.max(p.get_fill_opacity()))<=.001
                                    for p in root.label.family_members_with_points()))

    def test_revealing_a_route_marker_cannot_fill_over_the_city_label(self):
        from algovis import CityMap
        route=CityMap(['1','2'])
        operation=route.start_route();operation.begin();operation.finish()
        self.assertEqual(float(np.max(route.traveler.get_fill_opacity())),0)
        self.assertGreater(float(np.max(route.traveler.get_stroke_opacity())),0)

    def test_reusing_an_unplayed_refinement_carries_its_latest_content_into_a_new_layout(self):
        first=ColumnSlide()
        actor=first.add('recurrence',Equation({'call':'f(i)','eq':'=','value':r'\text{best value}'}))
        second=first.fork().revise('recurrence',{'call':'f(i,w)','eq':'=','value':'f(i+1,w)'})
        third=CenteredScene();third.add('recurrence',actor)
        self.assertEqual(actor.mobject.slot_tex['call'],'f(i)')
        self.assertEqual(first.target('recurrence').slot_tex['call'],'f(i)')
        self.assertEqual(third.target('recurrence').slot_tex,second.target('recurrence').slot_tex)
        copied=actor.copy()
        self.assertEqual(copied.mobject.slot_tex,second.target('recurrence').slot_tex)
        self.assertEqual(actor.part('value').tex,'f(i+1,w)')
        film=LessonAnimation();group=film.group('Whole recurrence')
        for view in (first,second,third):group.add(view,reason='Build the recurrence')
        group.compile()
        self.assertEqual(group.beats[-1].scene.target('recurrence').slot_tex['call'],'f(i,w)')
        self.assertEqual(first.target('recurrence').slot_tex['call'],'f(i)')

    def test_domino_conversion_retains_the_proposition_inside_its_falling_frame(self):
        from algovis import InductionChain,ViewScene
        chain=InductionChain(3)
        scene=ViewScene();scene.setup();scene.add(chain)
        operation=chain.as_dominoes()
        compiled=scene._compile_view_native(operation)
        self.assertIs(compiled.operations[0],operation)
        operation._setup_scene(scene);operation.begin();operation.finish();operation.clean_up_from_scene(scene)
        for case in chain.cases:
            np.testing.assert_allclose(case.label.get_center(),case.box.get_center())
            self.assertLess(case.label.width,case.box.width)
        for left,right in zip(chain.cases,chain.cases[1:]):
            self.assertGreater(right.label.get_left()[0]-left.label.get_right()[0],.1)
        falling=chain.fall(0);falling._setup_scene(scene);falling.begin();falling.interpolate(.5)
        for case in chain.cases:
            from algovis.review.inspection import visible_opacity
            self.assertGreater(visible_opacity(case.label),.9)
        for case in chain.cases:
            # Asymmetric glyph ink can shift its bounding-box center slightly
            # under rigid rotation. It must remain inside its physical domino.
            self.assertLess(np.linalg.norm(case.label.get_center()-case.box.get_center()),.03)
        self.assertTrue(all(float(np.max(part.get_stroke_opacity()))==0
            for part in chain.arrows.family_members_with_points()))
        falling.finish()

    def test_future_leaf_counts_reserve_space_without_revealing_or_replacing_nodes(self):
        def branch(n):return f'f({n})',[] if n<=2 else [(n-1,),(n-2,)]
        tree=RecursiveTree(branch,(4,),profile='compact')
        first=TreeScene();first.add('tree',tree,slot='diagram')
        second=first.fork().refine('tree',leaf_counts=True)
        self.assertFalse(hasattr(tree,'leaf_numbers'))
        self.assertEqual(second.target('tree').leaf_numbers.get_fill_opacity(),0)
        nodes=[data['mobject'] for data,_ in tree.iter_nodes()]
        scene=Scene();first.install(scene);apply(ViewTransition(first,second),scene)
        self.assertEqual([data['mobject'] for data,_ in tree.iter_nodes()],nodes)
        self.assertEqual(tree.leaf_numbers.get_fill_opacity(),0)
        self.assertIn(tree.leaf_numbers,tree.submobjects)
        self.assertEqual(len(tree.leaf_numbers),sum(not data['children'] for data,_ in tree.iter_nodes()))
        counter=tree.count_leaves();start(counter,scene);finish(counter,scene)
        self.assertTrue(all(label.get_fill_opacity()>.9 for label in tree.leaf_numbers))

    def test_freezing_and_group_fitting_preserve_a_definition_transfer_exactly_once(self):
        from algovis import SceneSequence,ApplyDefinition
        first=ColumnSlide()
        definition=first.add('definition',Equation({'value':r'\frac{k(k+1)}2'}))
        first.add('work',Equation({'call':'f(k+1)','eq':'=','child':'f(k)','rest':'+(k+1)'}))
        second=first.fork().substitute('work',child=r'\frac{k(k+1)}2',from_definition=definition.part('value'))
        third=second.fork();third.add('note','Now use the resulting expression.')
        group=SceneSequence('the whole calculation')
        for view in (first,second,third):group.add(view,reason='Develop the same calculation')
        group.compile()
        self.assertEqual([len(beat.scene.definition_uses) for beat in group.beats],[0,1,0])
        scene=Scene();prior=[None]
        def transition(view,**options):
            apply(ViewTransition(prior[0],view),scene);prior[0]=view
        with patch('algovis.composition.ApplyDefinition.bind',wraps=ApplyDefinition.bind) as transfer:
            group.play(SimpleNamespace(transition_to=transition))
        self.assertEqual(transfer.call_count,1)
    def test_planned_term_copies_preserve_semantic_color_without_early_resolution(self):
        first=ColumnSlide();handle=first.add('definition',Equation({'call':'f(k)'}))
        second=first.fork().revise('definition',{'call':'f(k)','eq':'=','value':'k+1'})
        second.set_meaning('definition',part='value',evaluation='good')
        source=second.part('definition','value')
        third=second.fork();third.add('application',Equation({'value':source}))
        self.assertNotIn('value',handle.mobject.parts)
        self.assertEqual(third.target('application').part('value').semantics.evaluation,'good')
        self.assertEqual(third.target('application').part('value').get_color(),DEFAULT_THEME.success)

    def test_definition_applications_can_target_a_case_equation_term(self):
        first=ColumnSlide();definition=first.add('definition',Equation({'value':'2'}))
        cases=CaseEquation(Equation({'f':'f[1,0]=\\max'}),
            [Equation({'skip':'f[2,0]'}),Equation({'value':'3','plus':'+','future':'f[2,2]'})])
        handle=first.add('choices',cases)
        second=first.fork().apply_definition('choices','row:1.future',definition.part('value'),'2')
        scene=Scene();first.install(scene)
        future=cases.rows[1].part('future')
        apply(ViewTransition(first,second),scene)
        self.assertIs(cases.rows[1].part('future'),future)
        self.assertEqual(cases.rows[1].slot_tex['future'],'2')
        self.assertEqual(cases.rows[1].native_layout_findings(),[])
        self.assertIs(handle.mobject,cases)

    def test_a_partial_tree_keeps_its_hidden_nodes_and_reveal_positions(self):
        def branch(n):return f'f({n})',[] if n<=2 else [(n-1,),(n-2,)]
        tree=RecursiveTree(branch,(4,),depth_limit=2,profile='compact',reveal_depth=0)
        first=TreeScene();first.add('tree',tree,slot='diagram')
        second=first.fork();second.add('caption','One child has appeared.',slot='explanation')
        scene=Scene();apply(ViewTransition(None,first),scene)
        a,b=tree.tree_structure['children']
        reveal=tree.get_node_reveal_anim(a);start(reveal,scene);finish(reveal,scene)
        second.retain_live_models(first)
        apply(ViewTransition(first,second),scene)
        self.assertAlmostEqual(b['shape'].get_stroke_opacity(),0)
        root=tree.tree_structure['mobject'].get_center().copy()
        destination=b['mobject'].get_center().copy()
        reveal=tree.get_node_reveal_anim(b);start(reveal,scene);finish(reveal,scene)
        np.testing.assert_allclose(tree.tree_structure['mobject'].get_center(),root)
        np.testing.assert_allclose(b['mobject'].get_center(),destination)
    def test_an_early_planned_scene_does_not_undo_cell_population(self):
        first=CenteredScene();sequence=StateSequence(['',''])
        first.add('sequence',sequence)
        second=first.fork();second.add('note','The value stays filled.')
        scene=Scene();first.install(scene)
        population=sequence.populate(0,1);start(population,scene);finish(population,scene)
        second.retain_live_models(first)
        self.assertEqual(second.target('sequence').cell(0).label.tex_string,'1')
        self.assertEqual(first.target('sequence').cell(0).label.tex_string,'')
        apply(ViewTransition(first,second),scene)
        self.assertEqual(sequence.cell(0).label.tex_string,'1')

    def test_layout_containers_preserve_children_without_moving_them_early(self):
        first=ColumnSlide();a=first.add('a',Equation({'value':'k+1'}));b=first.add('b','A definition')
        scene=Scene();first.install(scene)
        before=a.mobject.get_all_points().copy()
        group=MathStack(a.mobject,b.mobject)
        np.testing.assert_allclose(a.mobject.get_all_points(),before)
        second=ColumnSlide();second.add('group',group)
        apply(ViewTransition(first,second),scene)
        self.assertIs(group[0],a.mobject)
        self.assertIs(group[1],b.mobject)
    def test_managed_layouts_support_raster_and_vector_props(self):
        photo=ImageMobject(np.full((8,8,3),128,dtype=np.uint8))
        label=Text('A prop')
        prop=Group(photo,label)
        first=ColumnSlide();handle=first.add('prop',prop)
        scene=Scene();apply(ViewTransition(None,first),scene)
        self.assertIs(handle.mobject[0],photo)
        second=first.fork();second.add('explanation','The same prop stays visible.')
        apply(ViewTransition(first,second),scene)
        self.assertIs(handle.mobject[0],photo)
    def test_a_future_term_can_be_referenced_without_playing_its_scene_early(self):
        first=ColumnSlide();handle=first.add('definition',Equation({'call':'f(k)'}))
        second=first.fork().revise('definition',{'call':'f(k)','eq':'=','value':'k+1'})
        third=second.fork()
        copied=third.add('use',Equation({'value':second.part('definition','value')}))
        self.assertNotIn('value',handle.mobject.parts)
        self.assertEqual(third.target('use').slot_tex['value'],'k+1')
        scene=Scene();first.install(scene)
        apply(ViewTransition(first,second),scene)
        apply(ViewTransition(second,third),scene)
        self.assertEqual(copied.mobject.slot_tex['value'],'k+1')
    def test_equation_terms_can_be_borrowed_from_a_visible_definition(self):
        first=ColumnSlide()
        definition=first.add('definition',Equation({'call':'f(k)','eq':'=','value':'k+1'}))
        scene=Scene();first.install(scene)
        second=first.fork()
        source=definition.part('value')
        target=second.add('application',Equation({'call':'f(k)','eq':'=','value':source}))
        self.assertIs(second.target('application')._copy_sources['value'],source)
        apply(ViewTransition(first,second),scene)
        self.assertEqual(target.mobject.slot_tex['value'],'k+1')
        self.assertEqual(target.mobject.native_layout_findings(),[])
        self.assertEqual(len(scene.mobjects),2)
        third=second.fork().remove('definition')
        apply(ViewTransition(second,third),scene)
        fourth=third.fork();fourth.add('note','The copied result remains.')
        apply(ViewTransition(third,fourth),scene)
        self.assertIn(target.mobject,scene.mobjects)
    def test_equation_cases_retain_their_lhs_and_named_terms_when_refined(self):
        first=ColumnSlide()
        cases=CaseEquation(MathRow({'f':'f(', 'args':r'\ldots', 'close':')=\\max'}),
            [MathRow({'words':r'\text{take the item}'}),MathRow({'words':r'\text{skip the item}'})])
        handle=first.add('choices',cases)
        scene=Scene();first.install(scene)
        lhs=cases.lhs;argument=lhs.part('args')
        new_lhs=first.target('choices').lhs.next_layout(args='i,w')
        second=first.fork().refine('choices',lhs=new_lhs,rows=[
            MathRow({'value':'v_i+', 'future':'f(i+1,w+w_i)'}),
            MathRow({'future':'f(i+1,w)'})])
        apply(ViewTransition(first,second),scene)
        self.assertIs(cases.lhs,lhs)
        self.assertIs(cases.lhs.part('args'),argument)
        self.assertEqual(cases.lhs.slot_tex['args'],'i,w')
        self.assertEqual(cases.lhs.native_layout_findings(),[])
        self.assertEqual(len(scene.mobjects),1)

    def test_a_timeline_freezes_scene_plans_and_plays_only_new_beats(self):
        calls=[]
        renderer=SimpleNamespace(transition_to=lambda view,**options:calls.append((view,options)))
        film=LessonAnimation();view=ColumnSlide();view.add('meaning','A definition')
        film.add(view,reason='Introduce the definition')
        view.add('extra','A later fact')
        film.play(renderer);film.play(renderer)
        self.assertEqual(len(calls),1)
        self.assertNotIn('extra',calls[0][0].items)
        film.add(view,reason='Add the next fact');film.play(renderer)
        self.assertEqual(len(calls),2)


if __name__=='__main__':unittest.main()
