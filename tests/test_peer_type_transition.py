import unittest
import warnings

from manim import Scene

from algovis import ColumnSlide, MathRow, ViewTransition
from tests.test_composition import start, finish


class PeerTypeTransitionTests(unittest.TestCase):
    def test_case_call_refinement_retains_the_visible_optimizer_throughout(self):
        import numpy as np
        from algovis import CaseEquation
        first=ColumnSlide()
        rule=first.add('rule',CaseEquation(
            MathRow({'call':'f(i)','eq':'=','optimizer':r'\max'}),
            [MathRow({'take':r'\text{take}'}),MathRow({'skip':r'\text{skip}'})]))
        second=first.fork().refine('rule',call='f(i,w)')
        scene=Scene();first.install(scene)
        optimizer=rule.mobject.lhs.part('optimizer')
        plan=ViewTransition(first,second)
        animation=plan.animations(scene)[0];start(animation,scene)
        for alpha in np.linspace(0,1,31):
            animation.interpolate(alpha)
            self.assertIs(rule.mobject.lhs.part('optimizer'),optimizer)
            painted=[p for p in optimizer.get_family() if p.has_points()]
            self.assertTrue(painted)
            self.assertTrue(all(p.get_fill_opacity()>.99 for p in painted))
            self.assertIn(id(optimizer),{id(p) for p in scene.get_mobject_family_members()})
        finish(animation,scene);plan.commit(scene)
        self.assertIs(rule.mobject.lhs.part('optimizer'),optimizer)
        self.assertEqual(rule.mobject.lhs.slot_tex['call'],'f(i,w)')

    def test_definition_copies_land_with_the_destination_arguments_already_bound(self):
        from tests.test_composition import apply
        first=ColumnSlide()
        definition=first.add('definition',MathRow({'child':'f(n-1)','plus':'+','n':'n'}))
        goal=first.add('goal',MathRow({'call':'f(k+1)'}))
        second=first.fork().revise('goal',{'call':'f(k+1)','eq':'=',
            'child':'f(k+1-1)','plus':'+','n':'(k+1)'},from_definitions={
            'child':definition.part('child'),'plus':definition.part('plus'),'n':definition.part('n')})
        scene=Scene();first.install(scene)
        apply(ViewTransition(first,second),scene)
        self.assertEqual(goal.mobject.slot_tex['child'],'f(k+1-1)')
        self.assertEqual(goal.mobject.slot_tex['n'],'(k+1)')
        self.assertEqual(definition.mobject.slot_tex['child'],'f(n-1)')
        self.assertEqual(definition.mobject.slot_tex['n'],'n')

    def test_new_peer_waits_for_retained_equation_to_finish_resizing(self):
        first=ColumnSlide()
        retained=first.add('definition',MathRow({'call':'f(n)','eq':'=','value':'n'}))
        second=first.fork()
        introduced=second.add('application',MathRow({'call':'f(2)','eq':'=','value':'2'}))
        # Reproduce two sequence scopes that share logical objects but have
        # different reserved fits. This intentionally injects their endpoints.
        first.target('definition').scale(.8)
        scene=Scene();first.install(scene)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',message='.*Unexplained direct target adjustment.*')
            plan=ViewTransition(first,second)
        animation=plan.animations(scene)[0];start(animation,scene)
        animation.interpolate(.1)
        family={id(p) for p in scene.get_mobject_family_members()}
        self.assertNotIn(id(introduced.mobject),family)
        finish(animation,scene);plan.commit(scene)
        family={id(p) for p in scene.get_mobject_family_members()}
        self.assertIn(id(retained.mobject),family)
        self.assertIn(id(introduced.mobject),family)

    def test_retained_peers_resize_together_despite_local_retirement_phases(self):
        import numpy as np
        from algovis.layout import measured_font_size
        first=ColumnSlide()
        definition=first.add('definition',MathRow({'call':'f(n)','eq':'=','value':'n'}))
        claim=first.add('claim',MathRow({'call':'P(k)', 'old':r'\quad\text{old claim}'}))
        second=first.fork().revise('claim',{'call':'P(k)','new':r'\quad\text{new claim}'})
        for item in first.items.values():item.target.scale(.8)
        scene=Scene();first.install(scene)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',message='.*Unexplained direct target adjustment.*')
            plan=ViewTransition(first,second)
        animation=plan.animations(scene)[0];start(animation,scene)
        for alpha in np.linspace(0,1,31):
            animation.interpolate(alpha)
            self.assertAlmostEqual(measured_font_size(definition.mobject.part('call')),
                                   measured_font_size(claim.mobject.part('call')),places=4)
        finish(animation,scene);plan.commit(scene)

    def test_case_retirement_does_not_let_a_moving_rail_cross_the_equation(self):
        import numpy as np
        from manim import Line,LEFT,RIGHT
        from algovis import CaseEquation
        first=ColumnSlide()
        rule=first.add('rule',CaseEquation(MathRow({'lhs':'f(n)='}),
            [MathRow({'old':r'\text{old case}'}),MathRow({'zero':'0'})]))
        rail=first.add('rail',Line((0,-1,0),(0,1,0)))
        first.target('rule').move_to((0,0,0))
        first.target('rail').set_x(first.target('rule').get_left()[0]-.2)
        second=first.fork().refine('rule',rows=[MathRow({'new':'n'}),MathRow({'zero':'0'})])
        left=first.target('rule').get_left()[0]+1.5
        second.target('rule').move_to((left,0,0),aligned_edge=LEFT)
        second.target('rail').set_x(left-.2)
        scene=Scene();first.install(scene)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',message='.*Unexplained direct target adjustment.*')
            plan=ViewTransition(first,second)
        animation=plan.animations(scene)[0];start(animation,scene)
        for alpha in np.linspace(0,1,41):
            animation.interpolate(alpha)
            # Native row anchors remain at their prior location until adoption;
            # measure the actual painted term rather than those invisible points.
            self.assertGreater(rule.mobject.lhs.part('lhs').get_left()[0]-rail.mobject.get_x(),.05)
        finish(animation,scene);plan.commit(scene)


if __name__=='__main__':
    unittest.main()
