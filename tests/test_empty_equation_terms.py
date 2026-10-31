import unittest
from algovis import Equation,ListScene
from manim import FadeIn,Transform


class EmptyEquationTermTests(unittest.TestCase):
    def test_blank_slots_do_not_steal_neighboring_glyphs(self):
        row=Equation({'before':'','a':'a','middle':'','plus':'+','b':'b','after':''})
        self.assertEqual(list(row.parts),list(row.slot_tex))
        for key in ('a','plus','b'):
            self.assertEqual(row.part(key).tex_string,row.slot_tex[key])
        for key in ('before','middle','after'):
            self.assertEqual(row.part(key).width,0)
            self.assertEqual(row.part(key).height,0)
        self.assertEqual(row.native_layout_findings(),[])

    def test_blank_named_result_can_be_substituted_and_enters_in_place(self):
        row=Equation({'call':'f(k)','eq':'=','value':''})
        view=ListScene();view.add('row',row)
        next_view=view.fork().substitute('row',value=r'\frac{k(k+1)}2')
        destination=next_view.target('row')
        introductions=[];retirements=[]
        motions=row.motions_to(destination,introductions=introductions,retirements=retirements)
        self.assertIn(destination.part('value'),introductions)
        self.assertFalse(any(isinstance(m,Transform) and m.mobject is row.part('value') for m in motions))
        row.adopt_layout(destination)
        self.assertEqual(row.part('value').tex_string,r'\frac{k(k+1)}2')
        self.assertEqual(row.native_layout_findings(),[])
