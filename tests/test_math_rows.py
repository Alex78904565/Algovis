import unittest
import numpy as np
from manim import BLUE, Scene, Transform
from algovis import ApplyDefinition, MathRow


class MathRowTests(unittest.TestCase):
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

    def test_additive_worked_examples_cannot_publish_an_incorrect_equality(self):
        row=MathRow({'immediate':'5','plus':'+','future':'0','eq':'=','total':'0'}).require_sum()
        self.assertEqual(row.native_layout_findings()[0]['expected'],5)
        other=row.next_layout(immediate='0',future='6',total='6')
        self.assertEqual(other.native_layout_findings(),[])


if __name__=='__main__': unittest.main()
