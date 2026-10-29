import unittest
import numpy as np
from manim import BLUE, DOWN, MathTex, Scene, Transform, VGroup, VectorizedPoint
from algovis import ApplyDefinition, MathRow


class MathRowTests(unittest.TestCase):
    def test_partial_call_adoption_does_not_unhide_future_arguments(self):
        row=MathRow({'f':'f','open':'(','state':'s','close':')'})
        target=MathRow({'f':'f','open':'(','i':'i+1','comma':',','w':'w','close':')'})
        for name in ('i','comma','w'):target.part(name).set_opacity(0)
        scene=Scene();scene.add(row);row.commit(target,scene)
        for name in ('i','comma','w'):
            self.assertTrue(all(np.max(p.get_fill_opacity())==0 for p in row.part(name).family_members_with_points()))
        self.assertEqual(row.native_layout_findings(),[])
        self.assertTrue(any(np.max(p.get_fill_opacity())>0 for p in row.part('f').family_members_with_points()))

    def test_tex_selection_follows_the_adopted_terms_rather_than_retired_glyphs(self):
        row=MathRow({'call':'f(','argument':'i','close':')'})
        target=row.next_layout(argument='1')
        scene=Scene();scene.add(row);row.commit(target,scene)
        self.assertIs(row.get_part_by_tex('1'),row.part('argument'))
        self.assertIsNone(row.get_part_by_tex('i'))
        row.set_color_by_tex('1',BLUE)
        self.assertEqual(row.part('argument').get_color(),BLUE)

    def test_token_adapter_matches_existing_mathtex_default_and_explicit_sizes(self):
        self.assertAlmostEqual(MathRow.tokens('f(','i',')').scale(.7).font_size,33.6)
        self.assertAlmostEqual(MathRow.tokens('f(','i',')',font_size=40).scale(.7).font_size,28)

    def test_adopting_a_scaled_target_does_not_apply_its_scale_twice(self):
        row=MathRow.tokens('f(','i',')',font_size=48).scale(.7)
        target=MathRow.tokens('f(','1',')',font_size=48).scale(.7).aligned_to(row)
        scene=Scene();scene.add(row)
        row.commit(target,scene)
        self.assertAlmostEqual(row.font_size,33.6)
        following=row.next_layout(parts={**row.slot_tex,'1':'0'})
        self.assertAlmostEqual(following.font_size,33.6)
        self.assertAlmostEqual(following.part('0').height,row.part('0').height)
        self.assertEqual(row.native_layout_findings(),[])

    def test_argument_substitutions_preserve_the_actual_painted_color(self):
        row=MathRow({'f':'f(','i':'i','comma':',','w':'w','close':')'},color=BLUE)
        scene=Scene();scene.add(row)
        for changes in ({'i':'1'},{'w':'0'}):
            target=row.next_layout(**changes)
            for animation in row.motions_to(target):
                animation.begin();animation.interpolate(1);animation.finish()
            row.commit(target,scene)
            painted=[p for p in row.family_members_with_points() if np.max(p.get_fill_opacity())>.01]
            self.assertTrue(painted)
            self.assertTrue(all(p.get_fill_color()==BLUE for p in painted))

    def test_argument_replacement_uses_the_complete_tex_baseline(self):
        call=MathRow({'f':'f(','i':'i','comma':',','w':'w','close':')'})
        scene=Scene();scene.add(call)
        for changes in ({'i':'1'},{'w':'0'}):
            target=call.next_layout(**changes)
            self.assertAlmostEqual(target.baseline,call.baseline)
            for animation in call.motions_to(target):
                animation.begin();animation.interpolate(1);animation.finish()
            call.commit(target,scene)
            self.assertEqual(call.native_layout_findings(),[])
            self.assertAlmostEqual(call.font_size,33.6)
            self.assertEqual(scene.mobjects,[call])
        self.assertEqual(''.join(call.slot_tex.values()),'f(1,0)')

    def test_one_off_center_digit_is_rejected_even_at_the_correct_font_size(self):
        row=MathRow({'f':'f(2,','w':'3','close':')'})
        row.part('w').shift([0,-.12,0])
        self.assertEqual(row.native_layout_findings()[0]['part'],'w')
        self.assertAlmostEqual(row.font_size,33.6)

    def test_whole_row_motion_and_uniform_scaling_preserve_native_layout(self):
        row=MathRow({'a':'5','plus':'+','b':'0','eq':'=','c':'5'})
        row.scale(.77).shift([3,-2,0])
        self.assertEqual(row.native_layout_findings(),[])
        self.assertAlmostEqual(row.font_size,33.6*.77)

    def test_copying_a_definition_cannot_destroy_a_structured_call(self):
        source=MathRow({'f':'f(','i':'i','comma':',','w':'w','close':')'})
        destination=source.copy().shift([2,0,0])
        parts=dict(destination.parts)
        ApplyDefinition(source,None,destination)
        self.assertEqual(destination.parts,parts)
        self.assertEqual(destination.native_layout_findings(),[])

    def test_equivalent_group_to_editable_row_copy_keeps_glyphs_stable_on_arrival(self):
        source = VGroup(
            MathTex('(', 'n', r'\ \text{states}', ')'),
            MathTex(r'\times'),
            MathTex(r'(\le1\ \text{addition per state})'),
        ).arrange(buff=.16).scale(.72)
        destination = MathRow({
            'open': '(', 'n': 'n', 'units': r'\ \text{states})', 'times': r'\times',
            'work': r'(\le1\ \text{addition per state})',
        }, font_size=48*.72).shift(2*DOWN)
        parts = dict(destination.parts)
        glyphs = lambda mob: [p for p in mob.family_members_with_points()
                             if not isinstance(p, VectorizedPoint)]
        expected = [p.points.copy() for p in glyphs(destination)]
        transfer = ApplyDefinition(source, None, destination)
        # A composed sequence may move the reference before activating its copy.
        source.shift([1, .3, 0])
        original = source.get_all_points().copy()
        scene = Scene(); scene.add(source)
        transfer._setup_scene(scene); transfer.begin(); transfer.interpolate(0)
        for actual, reference in zip(glyphs(transfer.traveller), glyphs(source)):
            np.testing.assert_allclose(actual.points, reference.points)
        transfer.interpolate(.70)
        landed = [p.points.copy() for p in glyphs(transfer.traveller)]
        for alpha in (.75, .85, .95):
            transfer.interpolate(alpha)
            actual = glyphs(transfer.traveller)
            self.assertEqual(len(actual), len(expected))
            progress = transfer.animations[0].animations[1].rate_func((alpha-.7)/.3)
            for glyph, start, end in zip(actual, landed, expected):
                np.testing.assert_allclose(glyph.points, (1-progress)*start+progress*end, atol=1e-7)
        transfer.finish(); transfer.clean_up_from_scene(scene)
        np.testing.assert_allclose(source.get_all_points(), original)
        self.assertEqual(destination.parts, parts)
        self.assertEqual(destination.native_layout_findings(), [])
        self.assertNotIn(transfer.traveller, scene.get_mobject_family_members())
        for actual, points in zip(glyphs(destination), expected):
            np.testing.assert_allclose(actual.points, points)
        numerical = destination.next_layout(n='191')
        for motion in destination.motions_to(numerical):
            motion.begin(); motion.finish()
        destination.commit(numerical, scene)
        self.assertEqual(destination.slot_tex['n'], '191')
        self.assertEqual(destination.slot_tex['units'], r'\ \text{states})')
        self.assertIs(destination.part('units'), parts['units'])
        self.assertEqual(destination.native_layout_findings(), [])

    def test_additive_worked_examples_cannot_publish_an_incorrect_equality(self):
        row=MathRow({'immediate':'5','plus':'+','future':'0','eq':'=','total':'0'}).require_sum()
        self.assertEqual(row.native_layout_findings()[0]['expected'],5)
        other=row.next_layout(immediate='0',future='6',total='6')
        self.assertEqual(other.native_layout_findings(),[])


if __name__=='__main__': unittest.main()
