import unittest
from manim import MathTex, Scene, Text
from algovis import ColumnSlide, LessonTypography, MathRow, ProofSlide, SlideView, TextObject, DEFAULT_THEME
from tests.test_composition import apply
from algovis import ViewTransition


class SceneTypographyTests(unittest.TestCase):
    def test_chart_reflows_axes_while_keeping_scene_label_sizes(self):
        import math
        from algovis import DiagramScene,LogRuntimeComparison
        from algovis.layout import measured_font_size
        view=DiagramScene('Runtime')
        view.add('chart',LogRuntimeComparison([('n',lambda n:math.log10(n),'good')]),slot='diagram')
        view.add('caption',TextObject('Vertical units are powers of ten',type_role='label'),slot='explanation')
        view.validate()
        chart=view.target('chart')
        for label in [*chart.x_labels,*chart.y_labels,chart.y_title,*chart.legend]:
            self.assertAlmostEqual(measured_font_size(label),measured_font_size(view.target('caption')))

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
