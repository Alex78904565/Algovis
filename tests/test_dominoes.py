import math
import unittest
import numpy as np
from algovis import DominoGeometry


def corners(geometry, index, angle):
    x = index * geometry.pitch
    local = np.array([[-geometry.width, 0], [0, 0], [0, geometry.height],
                      [-geometry.width, geometry.height]])
    rotation = np.array([[math.cos(angle), math.sin(angle)],
                         [-math.sin(angle), math.cos(angle)]])
    return local @ rotation.T + [x, 0]


def separation(a, b):
    """Largest separating-axis gap: zero at contact, negative if overlapping."""
    gaps=[]
    for polygon in (a,b):
        for edge in np.roll(polygon,-1,axis=0)-polygon:
            normal=np.array([-edge[1],edge[0]])
            normal/=np.linalg.norm(normal)
            pa,pb=a@normal,b@normal
            gaps.append(max(pb.min()-pa.max(),pa.min()-pb.max()))
    return max(gaps)


class DominoGeometryTests(unittest.TestCase):
    def test_fall_maintains_contact_without_intersections(self):
        geometry=DominoGeometry(.42,1.30,.25)
        for front in range(5):
            limit=math.pi/2 if front==4 else geometry.first_contact
            for angle in np.linspace(0,limit,81):
                angles=geometry.angles(5,front,float(angle))
                bodies=[corners(geometry,i,a) for i,a in enumerate(angles)]
                for i in range(5):
                    self.assertGreaterEqual(bodies[i][:,1].min(),-1e-10)
                    for j in range(i+1,5):
                        self.assertGreaterEqual(separation(bodies[i],bodies[j]),-1e-9)
                for i in range(front):
                    self.assertAlmostEqual(separation(bodies[i],bodies[i+1]),0,places=8)

    def test_final_chain_rests_on_neighbors_with_last_domino_flat(self):
        geometry=DominoGeometry(.42,1.30,.25)
        angles=geometry.angles(5,4,math.pi/2)
        self.assertTrue(all(0<a<math.pi/2 for a in angles[:-1]))
        self.assertEqual(angles[-1],math.pi/2)
        self.assertLess(angles[0],angles[-2])

    def test_front_switch_does_not_jump(self):
        geometry=DominoGeometry(.42,1.30,.25)
        for front in range(4):
            np.testing.assert_allclose(geometry.angles(5,front,geometry.first_contact),
                                       geometry.angles(5,front+1,0),atol=1e-12)
