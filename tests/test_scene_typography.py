import unittest
from manim import MathTex, Scene, Text
from algovis import ColumnSlide, LessonTypography, MathRow, ProofSlide, SlideView, TextObject, DEFAULT_THEME
from tests.test_composition import apply
from algovis import ViewTransition


class SceneTypographyTests(unittest.TestCase):
    def test_derivation_footer_copy_bypasses_the_parameter_explanation(self):
        from algovis import DerivationScene
        import numpy as np
        view=DerivationScene()
        view.add('meaning',TextObject('Minimum additional distance'),slot='meaning')
        view.add('recurrence',MathRow({'value':'d(i,j)'}),slot='equation')
        view.add('parameters',TextObject('i = current city; v = visit pattern'),slot='explanation')
        definition=view.add('distance',MathRow({'call':'d(i,j)','meaning':r'=\text{distance}'}),slot='footer')
        view.install(Scene())
        source=definition.part('call').mobject
        destination=view.target('recurrence').part('value')
        route=view.definition_route(source,destination)
        self.assertTrue(route)
        obstacle=view.target('parameters')
        points=[source.get_center(),*route,destination.get_center()]
        half_width=max(source.width,destination.width)/2
        half_height=max(source.height,destination.height)/2
        for start,end in zip(points,points[1:]):
            for alpha in np.linspace(0,1,51):
                point=start+(end-start)*alpha
                self.assertFalse(obstacle.get_left()[0]-half_width<point[0]<obstacle.get_right()[0]+half_width
                    and obstacle.get_bottom()[1]-half_height<point[1]<obstacle.get_top()[1]+half_height)

    def test_column_definition_copy_bypasses_an_intervening_base_case(self):
        from algovis import Equation
        import numpy as np
        view=ColumnSlide()
        definition=view.add('definition',TextObject('Definition'))
        view.add('base',TextObject('Base case'))
        view.add('application',TextObject('Application'))
        scene=Scene();view.install(scene)
        source=definition.mobject;destination=view.target('application')
        route=view.definition_route(source,destination)
        self.assertEqual(len(route),2)
        base=view.target('base')
        for a in np.linspace(0,1,31):
            point=route[0]+a*(route[1]-route[0])
            self.assertFalse(base.get_left()[0]-source.width/2<point[0]<base.get_right()[0]+source.width/2)

    def test_selection_labels_share_one_fit_across_items_and_bag(self):
        from algovis import SelectionScene,MathStack
        from algovis.layout import measured_font_size
        from manim import Group,Rectangle
        view=SelectionScene()
        view.add('items',TextObject('Item labels',type_role='label'),slot='items')
        # The container is tall enough to require automatic fitting.
        view.add('bag',Group(Rectangle(width=1,height=3),
            TextObject('Bag label',type_role='label')),slot='bag')
        view.add('total',MathRow({'value':'1+3+1=5'}),slot='calculation')
        view.validate()
        self.assertAlmostEqual(measured_font_size(view.target('items')),
            measured_font_size(view.target('bag')[1]))
        self.assertLess(measured_font_size(view.target('items')),view.typography.label)

    def test_regrouped_equation_adopts_destination_peers_before_transition_commit(self):
        from algovis import CenteredScene,Equation
        from tests.test_composition import start,finish
        first=ColumnSlide(typography=LessonTypography(equation=30))
        retained=first.add('retained',Equation({'call':'f(k)'}))
        definition=first.add('definition',Equation({'value':'k+1'}))
        scene=Scene();first.install(scene)
        second=CenteredScene()
        second.add('retained',retained)
        second.add('application',Equation({'value':definition.part('value')}))
        transition=ViewTransition(first,second)
        for animation in transition.animations(scene):
            start(animation,scene)
            animation.interpolate(.5)
            self.assertTrue(retained.mobject._algovis_typography_group.startswith('transition/'))
            self.assertEqual(definition.mobject._algovis_typography_group,first._type_group)
            finish(animation,scene)
        # The arrived object is checked before ViewTransition.commit runs.
        self.assertEqual(retained.mobject._algovis_typography_group,second._type_group)
        from algovis.layout import measured_font_size
        self.assertAlmostEqual(measured_font_size(retained.mobject.part('call')),second.typography.equation)

    def test_chart_reflows_axes_while_keeping_scene_label_sizes(self):
        import math
        from algovis import DiagramScene,LogRuntimeComparison
        from algovis.layout import measured_font_size
        view=DiagramScene('Runtime')
        view.add('chart',LogRuntimeComparison([('n',lambda n:math.log10(n),'good')]),slot='diagram')
        view.add('caption',TextObject('Vertical units are powers of ten',type_role='label'),slot='explanation')
        view.validate()
        chart=view.target('chart')
        for label in [*chart.x_labels,*chart.y_labels]:
            self.assertAlmostEqual(measured_font_size(label),measured_font_size(view.target('caption')))
        # Axis/series descriptions are mathematical statements; tiny tick
        # numerals remain supporting labels. Neither shrinks with the axes.
        for label in [chart.y_title,*chart.legend]:
            self.assertAlmostEqual(measured_font_size(label),view.typography.equation)

    def test_reflow_preserves_semantic_color_as_well_as_typography(self):
        view=ColumnSlide()
        view.add('structure',TextObject('A definition',role='structure'))
        self.assertEqual(view.target('structure').get_color(),DEFAULT_THEME.role_color('structure'))
        view.add('bad',TextObject('An impractical runtime',evaluation='bad'))
        self.assertEqual(view.target('bad').get_color(),DEFAULT_THEME.danger)
    def test_raw_and_named_equations_receive_the_same_scene_default(self):
        view=ColumnSlide()
        raw=MathTex('f(k)')
        view.add('raw',raw)
        view.add('named',MathRow({'call':'f(k)'}))
        self.assertAlmostEqual(view.target('raw').font_size,33.6)
        self.assertAlmostEqual(view.target('named').font_size,33.6)
        self.assertAlmostEqual(raw.font_size,48)

    def test_supplied_sizes_cannot_change_a_scene_default(self):
        view=ColumnSlide()
        view.add('raw',MathTex('x').scale(.86))
        view.add('prose',Text('Explanation',font_size=42))
        self.assertAlmostEqual(view.target('raw').font_size,33.6)
        self.assertAlmostEqual(view.target('prose').font_size,26)

    def test_relative_override_requires_a_reason(self):
        view=ColumnSlide()
        with self.assertRaisesRegex(ValueError,'font_reason'):
            view.add('note','Supporting text',font_scale=.85)
        self.assertEqual(view.items,{})

    def test_scene_typography_survives_install_and_a_later_substitution(self):
        first=ColumnSlide()
        handle=first.add('call',MathRow({'call':'f(', 'index':'i', 'end':')'},font_size=48))
        scene=Scene();first.install(scene)
        self.assertAlmostEqual(handle.mobject.font_size,33.6)
        second=first.fork().substitute('call',index='1')
        apply(ViewTransition(first,second),scene)
        self.assertAlmostEqual(handle.mobject.font_size,33.6)
        self.assertEqual(handle.mobject.native_layout_findings(),[])
        self.assertTrue(handle.mobject._algovis_scene_typography)

    def test_a_proof_owns_its_label_and_equation_type_roles(self):
        view=ProofSlide()
        view.add('base_case',MathRow({'base':'f(0)=0'}))
        self.assertAlmostEqual(view.target('base_case').font_size,33.6)
        self.assertAlmostEqual(view.target('label:base_case').font_size,16)

    def test_scene_type_roles_can_be_configured_once(self):
        view=ColumnSlide(typography=LessonTypography(equation=30,body=24))
        view.add('equation',MathRow({'f':'f(i)'}))
        view.add('meaning','The value from this state')
        self.assertAlmostEqual(view.target('equation').font_size,30)
        self.assertAlmostEqual(view.target('meaning').font_size,24)


if __name__=='__main__':unittest.main()
