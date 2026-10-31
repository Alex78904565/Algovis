import unittest
import numpy as np
from manim import Scene
from manim.utils.paths import path_along_arc
from algovis import CaseEquation,Equation,Move,ViewScene
from tests.test_composition import start,finish


class MathTransferArcTests(unittest.TestCase):
    def check_transfer(self,source,parts):
        scene=ViewScene();scene.setup();scene.mount_view(source)
        target=source.copy().shift((2.,1.,0))
        angle=np.pi/3
        before=[part.get_center().copy() for part in parts]
        motion=scene._compile_view(Move(source,target,path_arc=angle))
        start(motion,scene);motion.interpolate(.5)
        curve=path_along_arc(angle)
        for part,point in zip(parts,before):
            expected=curve(point[None,:],(point+np.array([2.,1.,0]))[None,:],.5)[0]
            np.testing.assert_allclose(part.get_center(),expected,atol=1e-6)
        finish(motion,scene);scene.tear_down()

    def test_named_equation_terms_follow_the_containing_objects_arc(self):
        row=Equation({'call':'f(k)','eq':'=','value':'k+1'})
        self.check_transfer(row,[row.part(name) for name in row.parts])

    def test_case_brace_and_equations_follow_the_same_arc(self):
        cases=CaseEquation(Equation({'call':'f(k)','eq':'='}),[
            Equation({'first':'k+1'}),Equation({'second':'0'})])
        self.check_transfer(cases,[cases.brace,cases.lhs.part('call'),
                                   cases.rows[0].part('first'),cases.rows[1].part('second')])


if __name__=='__main__':unittest.main()
