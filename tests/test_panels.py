import unittest
import numpy as np
from manim import Scene, Square
from algovis import Panel, RowPanel, PanelSlide, SlideObject, SceneSequence, ViewTransition
from tests.test_composition import apply


class PanelTests(unittest.TestCase):
    def test_legacy_slot_alignment_overrides_are_rejected_instead_of_used(self):
        from algovis import SlotScene
        with self.assertRaisesRegex(TypeError,'Legacy block_slots'):
            class LegacySlots(SlotScene):
                block_slots=('one',)
        view=SlotScene()
        with self.assertRaises(AttributeError):view.block_slots=('main',)
        with self.assertRaisesRegex(ValueError,'alignment_reason'):
            Panel(center_block=False)

    def test_an_added_text_slot_is_measured_and_centered_without_registration(self):
        from algovis import SlotScene,Equation
        class NewSlot(SlotScene):
            ROWS=(('earlier',1),('new_text',1))
        view=NewSlot()
        view.add('one',Equation({'value':'T=2'}),slot='new_text')
        view.add('two',Equation({'value':'g_1=g_2=g_3=1'}),slot='new_text')
        self.assertIn('new_text',view.block_slots)
        content=__import__('manim').Group(view.target('one'),view.target('two'))
        self.assertAlmostEqual(content.get_x(),view._region('new_text').center[0],places=6)
        node=view.panels.children['new_text'].describe()
        self.assertTrue(node['usedOwnMeasurement'])
        self.assertGreater(node['measurement']['width'],0)
        self.assertEqual(node['layoutPath'],'algovis.panels.Panel.arrange')

    def test_unprepared_equation_placements_are_still_measured_by_the_panel(self):
        from algovis import Equation
        from algovis.composition import Placement
        equation=Equation({'value':'x+1'})
        item=Placement(SlideObject(equation),equation,'main')
        self.assertIsNone(item.ascent)
        measure=Panel.bound([('equation',item)]).measure()
        self.assertGreater(measure.width,0)
        self.assertGreater(measure.height,0)

    def test_every_slot_layout_executes_its_real_panel_owners(self):
        import algovis.scene_layouts as layouts
        from algovis.review.inspection import panel_path_findings
        classes={name:cls for name,cls in vars(layouts).items()
                 if isinstance(cls,type) and issubclass(cls,layouts.SlotScene)}
        for name,cls in classes.items():
            with self.subTest(layout=name):
                view=cls(pairs=[('left_object','right_object')]) if name=='PairedScene' else cls()
                for slot in view._slots():
                    key=slot+'_object' if name=='PairedScene' else 'object_'+slot
                    view.add(key,Square(.12),slot=slot)
                report=view.layout_report()
                self.assertEqual(report['compilerPath'],'recursive-panels')
                manifest={'viewInfrastructure':{'schema':2,'steps':[{'composition':report}]}}
                self.assertEqual(panel_path_findings(manifest,required=True),[])

    def test_a_parent_cannot_place_children_without_running_their_panel_path(self):
        from algovis.panels import RegionPanel,arrange_view
        class BrokenOwner(RegionPanel):
            def arrange(self,region=None):pass
        view=PanelSlide();panel=Panel();panel.add('object',Square(.4))
        view.add_panel('main',panel)
        root=BrokenOwner();root.in_region('main',view.layout.body,view.panels.children['main'])
        with self.assertRaisesRegex(RuntimeError,'layout path was not executed'):
            arrange_view(view,root)

    def test_publication_checks_actual_layout_paths_and_rejects_old_metadata(self):
        from algovis.review.inspection import panel_path_findings
        from copy import deepcopy
        view,_=self.board()
        manifest={'viewInfrastructure':{'schema':2,'steps':[{'composition':view.layout_report()}]}}
        self.assertEqual(panel_path_findings(manifest,required=True),[])
        broken=deepcopy(manifest)
        node=broken['viewInfrastructure']['steps'][0]['composition']['panelTree']['children']['body']['children']['left']
        node['usedOwnMeasurement']=False
        self.assertEqual(panel_path_findings(broken)[0]['kind'],'panel_measurement_bypassed')
        manifest['viewInfrastructure']['schema']=1
        self.assertEqual(panel_path_findings(manifest)[0]['kind'],'legacy_layout_trace')
        self.assertEqual(panel_path_findings({},required=True)[0]['kind'],'panel_layout_coverage_missing')
        self.assertEqual(panel_path_findings({'viewInfrastructure':{'schema':2,'steps':[]}},required=True)[0]['kind'],
                         'panel_layout_coverage_missing')

    def board(self):
        row=RowPanel(gap=1.)
        left=row.panel('left',Panel())
        handle=left.add('answer',Square(.6))
        row.panel('right',Panel())
        view=PanelSlide().add_panel('body',row)
        return view,handle

    def test_recursive_ownership_flattens_without_changing_live_geometry(self):
        view,handle=self.board()
        np.testing.assert_allclose(handle.mobject.get_center(),[0,0,0])
        self.assertIs(view.object('body/left/answer'),handle)
        self.assertEqual(set(view.panels.flatten()),set(view.items))
        self.assertIsInstance(view.panels.children['body'].children['left'],Panel)

    def test_fork_rebinds_every_leaf_to_its_own_detached_target(self):
        view,_=self.board();other=view.fork()
        for name,item in other.panels.flatten().items():
            self.assertIs(item,other.items[name])
            self.assertIsNot(item.target,view.items[name].target)

    def test_object_reparenting_is_a_global_move(self):
        first,handle=self.board()
        second=first.fork().reparent('body/left/answer','body/right/answer')
        plan=ViewTransition(first,second)
        self.assertEqual(plan.describe()['enter'],[])
        self.assertEqual(plan.describe()['exit'],[])
        self.assertIs(second.object('body/right/answer'),handle)

    def test_copies_keep_source_provenance_across_panels(self):
        first,handle=self.board();second=first.fork()
        second.add_at('body/right/copy',handle.copy())
        self.assertEqual(ViewTransition(first,second).describe()['copy'],['body/right/copy'])
        stage=Scene();first.install(stage);apply(ViewTransition(first,second),stage)
        self.assertIn(handle.mobject,stage.mobjects)
        self.assertIn(second.object('body/right/copy').mobject,stage.mobjects)

    def test_duplicate_ownership_requires_explicit_copy(self):
        first,handle=self.board()
        with self.assertRaisesRegex(ValueError,'two panel owners'):
            first.add_at('body/right/duplicate',handle)
        self.assertNotIn('body/right/duplicate',first.items)

    def test_panel_cycles_are_rejected(self):
        root=Panel();child=root.panel('child',Panel())
        with self.assertRaisesRegex(ValueError,'cycle'):child.panel('parent',root)

    def test_future_rows_reserve_space_without_being_visible(self):
        panel=Panel();panel.add('one',Square(.6))
        first=PanelSlide().add_panel('argument',panel)
        second=first.fork();second.add_at('argument/two',Square(1.))
        film=SceneSequence('complete nested argument')
        film.add(first,reason='First row');film.add(second,reason='Second row');film.compile()
        a,b=[beat.scene for beat in film.beats]
        np.testing.assert_allclose(a.target('argument/one').get_center(),b.target('argument/one').get_center())
        self.assertNotIn('argument/two',a.items)
        self.assertEqual(len(list(a.panels.leaves())),1)

    def test_late_growth_uses_one_fit_for_the_complete_explanation(self):
        panel=Panel();panel.add('one',Square(.6))
        first=PanelSlide().add_panel('argument',panel)
        second=first.fork();second.add_at('argument/wide',Square(5.))
        film=SceneSequence('growing nested argument')
        film.add(first,reason='First row');film.add(second,reason='Second row');film.compile()
        a,b=[beat.scene for beat in film.beats]
        self.assertEqual(a.items['argument/one'].fit_scale,b.items['argument/one'].fit_scale)
        np.testing.assert_allclose(a.target('argument/one').get_center(),b.target('argument/one').get_center())

    def test_remove_updates_the_owning_panel(self):
        view,_=self.board();view.remove('body/left/answer')
        self.assertEqual(view.items,{})
        self.assertEqual(list(view.panels.leaves()),[])

    def test_new_occupant_replaces_the_same_named_position(self):
        first,old=self.board()
        second=first.fork().replace_at('body/left/answer',Square(.9))
        plan=ViewTransition(first,second)
        self.assertEqual(plan.describe()['substitute'],['body/left/answer'])
        self.assertEqual(plan.describe()['enter'],[])
        self.assertEqual(plan.describe()['exit'],[])
        stage=Scene();first.install(stage);apply(plan,stage)
        self.assertNotIn(old.mobject,stage.mobjects)
        self.assertIn(second.object('body/left/answer').mobject,stage.mobjects)

    def test_hidden_future_nested_panel_reserves_its_internal_gaps(self):
        root=Panel();root.add('first',Square(.5))
        first=PanelSlide().add_panel('main',root)
        future=Panel(gap=.6);future.add('a',Square(.6));future.add('b',Square(.8))
        second=first.fork()
        second.add_panel_at('main/later',future)
        film=SceneSequence('future nested panel')
        film.add(first,reason='First');film.add(second,reason='Later');film.compile()
        a,b=[beat.scene for beat in film.beats]
        np.testing.assert_allclose(a.target('main/first').get_center(),b.target('main/first').get_center())
        self.assertEqual(len(list(a.panels.leaves())),1)

    def test_alignment_defaults_share_a_left_edge_and_center_the_block(self):
        panel=Panel();panel.add('small',Square(.6));panel.add('large',Square(1.2))
        view=PanelSlide().add_panel('argument',panel)
        a,b=[view.target('argument/'+name) for name in ('small','large')]
        self.assertAlmostEqual(a.get_left()[0],b.get_left()[0])
        self.assertAlmostEqual((a.get_top()[1]+b.get_bottom()[1])/2,view.layout.body.center[1])

    def test_every_exported_slide_uses_the_shared_recursive_arranger(self):
        import algovis
        from algovis import SlideView
        layouts={name:value for name,value in vars(algovis).items() if isinstance(value,type)
                 and issubclass(value,SlideView)}
        self.assertGreater(len(layouts),20)
        for name,cls in layouts.items():
            with self.subTest(layout=name):self.assertIs(cls._arrange,SlideView._arrange)

    def test_resolved_word_is_passed_to_each_object_once(self):
        from algovis import NarrationTrack,NarrationCue
        calls=[]
        class Observed(SlideObject):
            def next(self,context):
                calls.append(context)
                return super().next(context)
        root=Panel();nested=root.panel('nested',Panel());handle=Observed(Square(.6))
        nested.add('value',handle)
        first=PanelSlide().add_panel('main',root)
        second=first.fork().reparent('main/nested/value','main/value')
        stage=Scene();first.install(stage)
        stage.narration=NarrationTrack('unused',2,[NarrationCue('move',1,'move')],
            words=[{'word':'move','start':1.,'end':1.2}])
        stage._last_word_event={'cue':'move','edge':'start'}
        apply(ViewTransition(first,second),stage)
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0].event.cue,'move')
        self.assertEqual(calls[0].event.time,1.)
        self.assertEqual(calls[0].relation,'move')
        self.assertNotEqual(calls[0].arc,0.)

    def test_object_motion_declaration_is_consumed_by_the_compiler(self):
        from dataclasses import replace
        class CustomArc(SlideObject):
            def next(self,context):return replace(super().next(context),arc=.8)
        handle=CustomArc(Square(.5));panel=Panel();panel.add('value',handle)
        first=PanelSlide().add_panel('main',panel)
        second=first.fork();second.add_at('main/other',Square(.7))
        stage=Scene();first.install(stage);plan=ViewTransition(first,second);apply(plan,stage)
        self.assertEqual(plan.object_steps[id(handle.mobject)].arc,.8)


if __name__=='__main__':unittest.main()
