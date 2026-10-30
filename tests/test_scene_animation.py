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

    def test_domino_conversion_retains_readable_labels_below_the_falling_boxes(self):
        from algovis import InductionChain,ViewScene
        chain=InductionChain(3)
        scene=ViewScene();scene.setup();scene.add(chain)
        operation=chain.as_dominoes()
        compiled=scene._compile_view_native(operation)
        self.assertIs(compiled.operations[0],operation)
        operation._setup_scene(scene);operation.begin();operation.finish();operation.clean_up_from_scene(scene)
        label_positions=[case.label.get_center().copy() for case in chain.cases]
        for case in chain.cases:
            self.assertLess(case.label.get_top()[1],case.box.get_bottom()[1])
        for left,right in zip(chain.cases,chain.cases[1:]):
            self.assertGreater(right.label.get_left()[0]-left.label.get_right()[0],.1)
        falling=chain.fall(0);falling._setup_scene(scene);falling.begin();falling.interpolate(.5)
        for case in chain.cases:
            from algovis.review.inspection import visible_opacity
            self.assertGreater(visible_opacity(case.label),.9)
        for case,position in zip(chain.cases,label_positions):
            np.testing.assert_allclose(case.label.get_center(),position)
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
