import unittest
import warnings

from manim import Scene

from algovis import ColumnSlide, MathRow, ViewTransition
from tests.test_composition import start, finish


class PeerTypeTransitionTests(unittest.TestCase):
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
        animation.interpolate(.4)
        family={id(p) for p in scene.get_mobject_family_members()}
        self.assertNotIn(id(introduced.mobject),family)
        finish(animation,scene);plan.commit(scene)
        family={id(p) for p in scene.get_mobject_family_members()}
        self.assertIn(id(retained.mobject),family)
        self.assertIn(id(introduced.mobject),family)


if __name__=='__main__':
    unittest.main()
