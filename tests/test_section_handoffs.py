import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from manim import AnimationGroup, Circle, FadeIn, Group, ImageMobject, Rectangle, Scene, Text, VGroup, tempconfig

from algovis import SectionHandoff
from algovis.review.boundaries import compare_frames
from PIL import Image, ImageDraw


class SectionHandoffTests(unittest.TestCase):
    def test_round_trip_preserves_actual_painted_pixels_and_selectable_hierarchy(self):
        with tempfile.TemporaryDirectory() as directory, tempconfig({'pixel_width': 320, 'pixel_height': 180}):
            scene = Scene()
            label = Text('same work', font_size=27).shift([1, .4, 0])
            label._algovis_label = 'same work'
            hidden = Circle().set_opacity(0)
            shape = Rectangle(width=4, height=2, fill_color='#102030', fill_opacity=.6,
                              stroke_color='#ffcc55', stroke_width=3)
            image = ImageMobject(np.full((10, 14, 4), [30, 150, 60, 180], dtype=np.uint8))
            image.width = .8
            image.shift([-1, -.4, 0])
            scene.add(Group(VGroup(shape, label, hidden), image))
            scene.camera.capture_mobjects(scene.mobjects)
            before = scene.camera.pixel_array.copy()
            path = Path(directory)/'handoff.json'
            SectionHandoff.save(scene, path)
            restored = SectionHandoff.load(scene, path)
            scene.clear(); scene.add(restored); scene.camera.reset()
            scene.camera.capture_mobjects(scene.mobjects)
            np.testing.assert_array_equal(before, scene.camera.pixel_array)
            self.assertEqual(restored[0][0][1]._algovis_label, 'same work')
            self.assertEqual(restored[0][0][2].get_fill_opacity(), 0)

    def test_marker_exclusion_does_not_remove_other_content(self):
        with tempfile.TemporaryDirectory() as directory:
            scene = Scene(); marker, content = Text('chapter'), Rectangle()
            scene.add(marker, content)
            path = Path(directory)/'frame.json'
            SectionHandoff.save(scene, path, exclude=(marker,))
            restored = SectionHandoff.load(scene, path)
            self.assertEqual(len(restored), 1)
            np.testing.assert_array_equal(restored[0].points, content.points)

    def test_corrupt_missing_and_incompatible_frames_fail_clearly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'frame.json'; scene = Scene()
            with self.assertRaisesRegex(FileNotFoundError, 'preceding section'):
                SectionHandoff.load(scene, path)
            SectionHandoff.save(scene, path)
            data = json.loads(path.read_text()); data['background'] = '#ffffff'
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Invalid section'):
                SectionHandoff.load(scene, path)
            SectionHandoff.save(scene, path)
            scene.camera.frame_width += 1
            with self.assertRaisesRegex(ValueError, 'matching camera'):
                SectionHandoff.load(scene, path)

    def test_transition_clears_before_reveal_with_no_added_time_or_premature_target(self):
        old, new = Rectangle(), Circle()
        scene = Scene(); scene.add(old)
        transition = SectionHandoff.transition(old, FadeIn(new), run_time=.6)
        self.assertAlmostEqual(transition.run_time, .6)
        self.assertNotIn(new, scene.get_mobject_family_members())
        self.assertIs(transition.animations[0].mobject, old)
        self.assertIsInstance(transition.animations[1], AnimationGroup)

    def test_actual_cut_comparison_detects_jump_and_only_ignores_declared_marker(self):
        first=Image.new('RGB',(320,180)); second=first.copy()
        ImageDraw.Draw(second).rectangle((1,1,50,8),fill='white')
        self.assertEqual(compare_frames(first,second)['status'],'fail')
        marker={'x':0,'y':0,'width':.2,'height':.06}
        self.assertEqual(compare_frames(first,second,ignore_regions=[marker])['status'],'pass')
        ImageDraw.Draw(second).rectangle((110,80,150,105),fill='white')
        self.assertEqual(compare_frames(first,second,ignore_regions=[marker])['status'],'fail')
        with self.assertRaisesRegex(ValueError,'entire frame'):
            compare_frames(first,second,ignore_regions=[{'x':0,'y':0,'width':1,'height':1}])


if __name__ == '__main__':
    unittest.main()
