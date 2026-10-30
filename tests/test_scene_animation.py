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
        with patch('algovis.composition.ApplyDefinition',wraps=ApplyDefinition) as transfer:
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
        with patch('algovis.composition.ApplyDefinition',wraps=ApplyDefinition) as transfer:
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
        with patch('algovis.composition.ApplyDefinition',wraps=ApplyDefinition) as transfer:
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
            with patch('algovis.composition.ApplyDefinition',wraps=ApplyDefinition) as transfer:
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
        with patch('algovis.composition.ApplyDefinition',wraps=ApplyDefinition) as transfer:
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
