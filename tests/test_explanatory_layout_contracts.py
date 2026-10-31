import unittest
from types import SimpleNamespace

import numpy as np
from manim import Scene
from algovis import (AnalysisScene,DerivationScene,Equation,FunctionDefinition,CaseEquation,
                     ColumnSlide,CityMap,DEFAULT_THEME)
from algovis.attention import attention_declaration


class ExplanatoryLayoutContracts(unittest.TestCase):
    def test_analysis_keeps_results_on_one_line_and_columns_off_the_margins(self):
        board=AnalysisScene()
        board.add('left',Equation({'time':'T(k)=2T(k-1)+O(1)'}),slot='left')
        board.add('right',Equation({'states':'(n+1)(C+1)'}),slot='right')
        board.add('a',Equation({'time':'O(2^n)'}),slot='left_result')
        board.add('b',Equation({'time':'O(nC)'}),slot='right_result')
        self.assertAlmostEqual(board.target('a').baseline,board.target('b').baseline,places=5)
        for name,slot in [('left','left'),('right','right')]:
            self.assertAlmostEqual(board.target(name).get_x(),board._region(slot).center[0],places=5)

    def test_derivation_is_one_common_edge_centered_argument(self):
        board=DerivationScene()
        for name,slot,tex in [('meaning','meaning','f(i,w)=v'),('rule','equation','f(i,w)=f(i+1,w)'),('state','explanation','i=1')]:
            board.add(name,Equation({'body':tex}),slot=slot)
        mobs=[board.target(k) for k in ('meaning','rule','state')]
        self.assertLess(max(m.get_left()[0] for m in mobs)-min(m.get_left()[0] for m in mobs),1e-6)
        envelope=np.array([min(m.get_left()[0] for m in mobs),max(m.get_right()[0] for m in mobs)])
        self.assertAlmostEqual(envelope.mean(),board.layout.body.center[0],places=5)

    def test_default_block_policy_includes_optional_context(self):
        from algovis import MapScene
        board=MapScene(context=True)
        board.add('instance',Equation({'capacity':'T=2'}),slot='meaning')
        board.add('cost',FunctionDefinition('p_k(b)','cost of buying b units'),slot='context')
        self.assertIn('context',board.block_slots)
        self.assertTrue(board.validate())

    def test_argument_reference_and_body_share_the_sequence_type_scale(self):
        from algovis.sequence_layout import plan_sequence
        from algovis.fitting import font_sizes
        board=DerivationScene()
        board.add('rule',Equation({'rule':'f(i,j)=f(i+1,j)+f(i,j+1)'}),slot='equation')
        board.add('reference',FunctionDefinition('d(i,j)','distance from city i to city j'),slot='footer')
        later=board.fork().substitute('rule',rule='f(i,j)=f(i+1,j)+f(i,j+1)+f(i+1,j+1)+f(i+2,j+2)')
        views,_=plan_sequence('a growing argument keeps its reference type scale',[board,later])
        for view in views:
            body=font_sizes(view.target('rule'))
            reference=font_sizes(view.target('reference'))
            self.assertAlmostEqual(body[0],reference[0],places=5)

    def test_reflow_waits_for_a_copied_definition_to_retire(self):
        from unittest.mock import patch
        from algovis import ViewTransition,ApplyDefinition
        from algovis.sequence_layout import plan_sequence
        from tests.test_composition import start,finish
        board=DerivationScene()
        board.add('rule',Equation({'call':'f(i,t)=','opt':r'\min','value':'f(i+1,t)'}),slot='equation')
        bound=board.add('bound',Equation({'label':r'\text{maximum purchase: }','value':'T-t'}),slot='explanation')
        price=board.add('price',FunctionDefinition('p_i(b)','cost to buy b units at city i'),slot='explanation')
        changed=board.fork().revise('rule',{'call':'f(i,t)=','opt':r'\min_{',
            'bound':bound.part('value'),'end':'}','value':'f(i+1,t)'})
        changed.remove('bound')
        views,_=plan_sequence('apply a bound and reclaim its row',[board,changed])
        renderer=Scene();views[0].install(renderer)
        plan=ViewTransition(*views)
        copies=[];factory=ApplyDefinition.bind
        def capture(*args,**kwargs):
            result=factory(*args,**kwargs);copies.append(result);return result
        with patch.object(ApplyDefinition,'bind',side_effect=capture):
            for animation in plan.animations(renderer):
                start(animation,renderer)
                for alpha in np.linspace(0,1,61):
                    animation.interpolate(float(alpha))
                    source=bound.mobject;moving=price.mobject
                    present={id(p) for p in renderer.get_mobject_family_members()}
                    visible=(any(id(p) in present for p in source.family_members_with_points())
                        and max(float(p.get_fill_opacity()) for p in source.family_members_with_points())>.02)
                    if visible:
                        self.assertTrue(moving.get_top()[1]<source.get_bottom()[1]+.01
                            or moving.get_bottom()[1]>source.get_top()[1]-.01,
                            'The retained price definition crossed a still-visible source row')
                        label=source.part('label')
                        for copy in copies:
                            traveller=copy.traveller
                            if id(traveller) not in present:continue
                            overlap=(min(traveller.get_right()[0],label.get_right()[0])
                                -max(traveller.get_left()[0],label.get_left()[0]),
                                min(traveller.get_top()[1],label.get_top()[1])
                                -max(traveller.get_bottom()[1],label.get_bottom()[1]))
                            self.assertFalse(min(overlap)>.015,'The travelling bound crossed its retained source label')
                finish(animation,renderer)
        plan.commit(renderer)
        np.testing.assert_allclose(price.mobject.get_center(),views[1].target('price').get_center())

    def test_whole_english_definition_has_a_clear_application_route(self):
        from algovis import ApplicationScene,ViewTransition
        from algovis.sequence_layout import plan_sequence
        from tests.test_composition import apply
        board=ApplicationScene()
        board.add('rule',CaseEquation(Equation({'call':'f(i,w)=','opt':r'\max'}),[
            Equation({'take':r'v_i+f(i+1,w+w_i)\quad\text{if }w+w_i\le C'}),
            Equation({'skip':'f(i+1,w)'})]),slot='reference')
        board.add('base',Equation({'base':'f(n+1,w)=0'}),slot='reference')
        board.add('conditions',Equation({'initial':r'\text{initial conditions: }i=1,\quad w=0'}),slot='conditions')
        meaning=board.add('meaning',FunctionDefinition('f(i,w)',
            'best additional value when item i is next, with w weight in the bag'),slot='definition')
        next_board=board.fork()
        next_board.add('instance',meaning.copy(),slot='application')
        next_board.refine('instance',call='f(1,0)',meaning='best additional value from all items, with an empty bag')
        views,_=plan_sequence('read the answer',[board,next_board])
        renderer=Scene();views[0].install(renderer)
        apply(ViewTransition(*views),renderer)
        self.assertTrue(views[1].validate())

    def test_new_formula_ink_waits_when_it_crosses_the_definition_copy_route(self):
        from unittest.mock import patch
        from algovis import ViewTransition,ApplyDefinition
        from algovis.sequence_layout import plan_sequence
        from tests.test_composition import start,finish
        board=DerivationScene()
        meaning=board.add('meaning',FunctionDefinition('f[1,v]',
            'minimum weight to reach at least v from all items'),slot='meaning')
        board.add('range',Equation({'range':'0\\le v\\le V'}),slot='explanation')
        feasible=board.add('feasible',Equation({'call':meaning.part('call'),'condition':'\\le C'}),slot='explanation')
        changed=board.fork()
        changed.add('answer',Equation({'opt':r'\max_{0\le v\le V\atop ',
            'call':feasible.part('call'),'end':r'\le C}v'}),slot='explanation')
        views,_=plan_sequence('read the largest feasible target',[board,changed])
        renderer=Scene();views[0].install(renderer)
        plan=ViewTransition(*views);copies=[];factory=ApplyDefinition.bind
        def capture(*args,**kwargs):
            motion=factory(*args,**kwargs);copies.append(motion);return motion
        inspected=False
        with patch.object(ApplyDefinition,'bind',side_effect=capture):
            for animation in plan.animations(renderer):
                start(animation,renderer)
                for alpha in np.linspace(0,1,61):
                    animation.interpolate(float(alpha))
                    present={id(p) for p in renderer.get_mobject_family_members()}
                    for motion in copies:
                        traveller=motion.traveller
                        if id(traveller) not in present:continue
                        if np.linalg.norm(traveller.get_center()-motion.result.get_center())<.02:continue
                        inspected=True
                        prefix=changed.object('answer').mobject.part('opt')
                        ink=prefix.family_members_with_points()
                        self.assertTrue(not any(id(p) in present for p in ink)
                            or max(float(p.get_fill_opacity()) for p in ink)<.01,
                            'The new maximum prefix appeared in the travelling definition route')
                finish(animation,renderer)
        plan.commit(renderer)
        self.assertTrue(inspected)
        self.assertTrue(views[1].validate())

    def test_sequence_reserves_a_corridor_for_a_cross_row_definition(self):
        from algovis import TextObject,ViewTransition,ApplyDefinition
        from algovis.sequence_layout import plan_sequence
        from tests.test_composition import start,finish
        from unittest.mock import patch
        board=DerivationScene()
        board.add('meaning',FunctionDefinition('f(i,v_1,\\ldots,v_n)',
            'minimum additional distance from city i to visit every unvisited city'),slot='meaning')
        board.add('recurrence',Equation({'call':r'f(i,v_1,\ldots,v_n)=',
            'opt':r'\min_{j:v_j=\mathrm{false}}','immediate':r'\text{immediate effect}',
            'plus':'+','future':r'\text{long-term effect}'}),slot='equation')
        choice=board.add('choice',TextObject('choose next city to visit'),slot='explanation')
        state=board.add('state',TextObject('i is the current city; each visit bit is true if its city is visited, false otherwise'),slot='explanation')
        distance=board.add('distance',FunctionDefinition('d(i,j)','distance from city i to city j'),slot='footer')
        changed=board.fork().substitute('recurrence',immediate='d(i,j)',from_definition=distance.part('call'))
        views,_=plan_sequence('a definition crosses the state explanation',[board,changed])
        self.assertGreater(views[0]._sequence_motion_margin,0.)
        self.assertEqual(views[0]._argument_region().width,views[1]._argument_region().width)
        renderer=Scene();views[0].install(renderer)
        plan=ViewTransition(*views);copies=[];factory=ApplyDefinition.bind
        def capture(*args,**kwargs):
            motion=factory(*args,**kwargs);copies.append(motion);return motion
        with patch.object(ApplyDefinition,'bind',side_effect=capture):
            for animation in plan.animations(renderer):
                start(animation,renderer)
                for alpha in np.linspace(0,1,81):
                    animation.interpolate(float(alpha))
                    for motion in copies:
                        for handle in (choice,state):
                            traveller=motion.traveller;ink=handle.mobject
                            overlap=(min(traveller.get_right()[0],ink.get_right()[0])-max(traveller.get_left()[0],ink.get_left()[0]),
                                     min(traveller.get_top()[1],ink.get_top()[1])-max(traveller.get_bottom()[1],ink.get_bottom()[1]))
                            self.assertFalse(min(overlap)>.015,
                                f'The detoured definition crossed an intervening explanation row: '
                                f'alpha={alpha}, traveller={traveller.get_center()}, row={ink.get_center()}, '
                                f'overlap={overlap}, via={motion.waypoint_positions}, '
                                f'destination={motion.result.get_center()}, row bounds={ink.get_corner(np.array([-1.,-1.,0.]))}/{ink.get_corner(np.array([1.,1.,0.]))}')
                finish(animation,renderer)
        plan.commit(renderer)

    def test_definition_has_the_same_named_colored_call_in_comparison_and_refinement(self):
        original=FunctionDefinition('f(i,w)','maximum additional value with w weight already in the bag')
        altered=original.with_state(call='f(i,v)',meaning='minimum weight needed to reach at least v value')
        self.assertEqual(original.part('call').semantics.role,'current')
        self.assertEqual(altered.part('call').semantics.role,'current')
        self.assertEqual(altered.slot_tex['call'],'f(i,v)')
        self.assertIn('minimum',altered.slot_tex['meaning'])

    def test_unbraced_single_result_sits_beside_equals_and_shares_baseline(self):
        rule=CaseEquation(Equation({'call':'f(n+1,w)','eq':'='}),[Equation({'zero':'0'})])
        self.assertLess(rule.rows[0].get_left()[0]-rule.lhs.get_right()[0],.2)
        self.assertAlmostEqual(rule.rows[0].baseline,rule.lhs.baseline,places=5)

    def test_case_term_roles_survive_new_rows_and_known_status_has_precedence(self):
        from algovis.semantics import set_semantics
        rule=CaseEquation(Equation({'call':'f(i)='}),[Equation({'future':'f(i+1)'})],
            term_roles={'future*':'structure'})
        changed=rule.with_state(rows=[Equation({'future':'f(i+2)'})])
        part=changed.rows[0].part('future')
        self.assertEqual(part.semantics.role,'structure')
        set_semantics(part,status='known')
        changed._paint_terms()
        self.assertEqual(part.semantics.status,'known')
        self.assertEqual(part.get_color(),DEFAULT_THEME.success)

    def test_one_attention_binding_can_box_two_related_live_totals(self):
        board=ColumnSlide();a=board.add('weight',Equation({'w':'w=5'}));b=board.add('value',Equation({'v':'v=21'}))
        scene=Scene();scene.theme=DEFAULT_THEME;scene.narration=SimpleNamespace(cues={'best':SimpleNamespace(phrase='best choice')})
        board.install(scene)
        binding=attention_declaration((a,b),'best',style='box',reason='Both properties describe the same choice')
        animation=binding.animation(scene)
        target=animation._algovis_focus_target
        self.assertEqual(len(target),2)
        self.assertLessEqual(target.get_bottom()[1],b.mobject.get_bottom()[1])
        self.assertGreaterEqual(target.get_top()[1],a.mobject.get_top()[1])

    def test_preparing_road_reveal_does_not_paint_future_roads(self):
        network=CityMap((1,2,3),show_roads=False)
        opacity=[r.get_stroke_opacity() for r in network.roads]
        network.reveal_roads()
        self.assertEqual(opacity,[r.get_stroke_opacity() for r in network.roads])
        self.assertTrue(all(v==0 for v in opacity))

    def test_dashboard_type_peers_belong_to_the_fitted_diagram(self):
        from algovis import MapScene,RoadTripSimulation
        board=MapScene(context=True)
        meaning=board.add('meaning',FunctionDefinition('p_k(b)','cost to buy b units at city k'),slot='context')
        trace=board.add('trace',RoadTripSimulation(capacity=2,prices=(4,2,5),consumption=(1,1,1)),slot='map')
        context_group=board.target('meaning').part('call')._algovis_typography_group
        dashboard=board.target('trace').state
        peers={part._algovis_typography_group for part in dashboard.parts.values()}
        self.assertEqual(len(peers),1)
        self.assertNotIn(context_group,peers)

    def test_log_chart_tick_density_tracks_the_declared_large_range(self):
        from algovis import LogRuntimeComparison
        plot=LogRuntimeComparison([('n',lambda n:n,'good')],x_max=100,y_max=160,
            x_ticks=(2,20,40,60,80,100),y_ticks=(0,40,80,120,160))
        self.assertLessEqual(len(plot.axes.y_axis.ticks),6)
        self.assertLessEqual(len(plot.axes.x_axis.ticks),7)

    def test_two_routes_share_one_blended_edge_with_theme_color_strings(self):
        from tests.test_composition import start,finish
        from manim import ManimColor,interpolate_color
        network=CityMap((1,2,3));stage=Scene();stage.add(network)
        first=network.route_step(0,1)
        start(first,stage);finish(first,stage)
        overlay=network.route_overlays[(0,1)]
        second=network.route_step(1,0,evaluation='good')
        start(second,stage);finish(second,stage)
        self.assertEqual(len(network.route_overlays),1)
        self.assertIs(network.route_overlays[(0,1)],overlay)
        expected=interpolate_color(ManimColor(DEFAULT_THEME.primary),ManimColor(DEFAULT_THEME.success),.5)
        self.assertEqual(overlay.get_stroke_color(),expected)

    def test_flat_and_nested_applications_bind_arguments_during_travel(self):
        from unittest.mock import patch
        from algovis import ApplyDefinition,ViewTransition,RecurrenceScene
        from tests.test_composition import apply
        factory=ApplyDefinition.bind;transfers=[]
        def capture(*args,**kwargs):
            motion=factory(*args,**kwargs);transfers.append(motion);return motion
        for nested in (False,True):
            first=RecurrenceScene()
            if nested:
                handle=first.add('rule',CaseEquation(Equation({'call':'f(i,v)','opt':r'=\min'}),
                    [Equation({'future':r'\text{remaining weight}'})]),slot='equation')
                second=first.fork().apply_definition('rule','row:0.future',handle.part('lhs.call'),'f(i+1,v)')
            else:
                handle=first.add('rule',Equation({'call':'f(i,v)','eq':'=','future':r'\text{remaining weight}'}),slot='equation')
                second=first.fork().substitute('rule',future='f(i+1,v)',from_definition=handle.part('call'))
            renderer=Scene();first.install(renderer)
            with patch.object(ApplyDefinition,'bind',side_effect=capture):
                apply(ViewTransition(first,second),renderer)
        self.assertEqual(len(transfers),2)
        for motion in transfers:
            self.assertTrue(motion._algovis_copy_contract['formattingDuringTravel'])
            self.assertIs(motion.landing,motion.result)

    def test_pause_only_retiming_keeps_word_durations_and_expands_containers(self):
        from tools.audio_pipeline import retime_after_inserted_pause
        source={'segments':[{'start':1.,'end':5.}],
            'words':[{'word':'before','start':1.,'end':2.},{'word':'after','start':4.,'end':5.}],
            'cues':[{'phrase':'after','time':4.}]}
        target=retime_after_inserted_pause(source,3.,2.5)
        self.assertEqual(target['segments'][0]['end'],7.5)
        self.assertEqual(target['words'][0],source['words'][0])
        self.assertEqual(target['words'][1]['start'],6.5)
        self.assertEqual(target['words'][1]['end']-target['words'][1]['start'],1.)
        self.assertEqual(target['cues'][0]['time'],6.5)
        self.assertEqual(source['words'][1]['start'],4.)
        with self.assertRaises(ValueError):
            retime_after_inserted_pause({'words':[{'word':'speech','start':2.,'end':4.}]},3.,2.)

    def test_refined_container_normalizes_borrowed_fitted_children_before_planning(self):
        from algovis import MathStack,ProofSlide,TextObject
        from algovis.presentation import SlideLayout
        from algovis.layout import measured_font_size
        from algovis.sequence_layout import plan_sequence
        # A larger title region exercises the library's normal fitted path.
        proof=ProofSlide(profile='worked',layout=SlideLayout(header_height=2.))
        proof.define_algorithm(CaseEquation(Equation({'call':'f(i,w)=','opt':r'\max'}),[
            Equation({'take':r'v_i+f(i+1,w+w_i)','if':r'\quad\text{if }w+w_i\le C'}),
            Equation({'skip':'f(i+1,w)'})]),
            CaseEquation(Equation({'call':'f(n,w)='}),[
                Equation({'take':r'v_n\quad\text{if }w+w_n\le C'}),
                Equation({'skip':r'0\quad\text{otherwise}'})]))
        proof.add('claim',TextObject('P(k): the answer is optimal with at most k items left.'))
        proof.add('base_case',TextObject('One item: take it if it fits; otherwise take nothing.'))
        proof.add('induction_hypothesis',TextObject('Assume both child answers are optimal.'))
        proof.add('inductive_step',Equation({'call':'f(i,w)','context':r'\quad(k+1\text{ items})'}))
        proof.add('work',MathStack(TextObject('By P(k), both child calls give the best remaining values.'),
                                  Equation({'best':r'\max\{\text{best taking }i,\text{best skipping }i\}'})))
        self.assertLess(proof.items['work'].fit_scale,1.)
        borrowed=proof.target('work')[0]
        revised=proof.fork().refine('work',rows=[borrowed,Equation({'best':r'\max\{f(k,w),v_{k-1}+f(k,w+w_{k-1})\}'})])
        item=revised.items['work']
        self.assertAlmostEqual(measured_font_size(item.target[0])/item.fit_scale,
                               revised.typography.body,places=5)
        views,_=plan_sequence('continuing proof',[proof,revised])
        renderer=Scene();previous=None
        for view in views:
            view.retain_live_models(previous)
            view.install(renderer);previous=view

    def test_appending_a_consequence_keeps_the_existing_justification_object(self):
        from algovis import MathStack,TextObject,ViewTransition
        from algovis.sequence_layout import plan_sequence
        from tests.test_composition import apply
        first=ColumnSlide()
        reason=first.add('work',TextObject('Both child calls give optimal remaining values.'))
        second=first.fork().remove('work')
        work=second.add('work',MathStack(reason.mobject,
            Equation({'consequence':r'\max\{\text{take},\text{skip}\}'})))
        views,_=plan_sequence('retain the reason and add the consequence',[first,second])
        renderer=Scene();views[0].install(renderer)
        original=reason.mobject
        apply(ViewTransition(*views),renderer)
        self.assertIs(work.mobject[0],original)
        self.assertEqual(len(work.mobject),2)


if __name__=='__main__':unittest.main()
