import unittest
from types import SimpleNamespace

from manim import RIGHT, Square, Text, VGroup, WHITE
from algovis import SlideScene
from algovis.review.inspection import capture_snapshot, visible_opacity


class RenderInspectionTests(unittest.TestCase):
    def test_text_color_comes_from_visible_glyphs_not_svg_container_default(self):
        label=Text('known value',color=WHITE,font_size=24)
        data=capture_snapshot(self.scene(label),14,8)
        item=next(obj for obj in data['objects'] if obj['kind']=='Text')
        self.assertEqual(item['paintColors'],['#FFFFFF'])
        self.assertEqual(item['color'],'#FFFFFF')

    def scene(self, *objects):
        scene = object.__new__(SlideScene)
        scene.mobjects = list(objects)
        scene._review_object_ids = {}
        scene._review_next_object_id = 1
        scene.renderer = SimpleNamespace(time=2)
        return scene

    def test_hidden_objects_do_not_cover_selectable_visible_objects(self):
        hidden, visible = Square().set_opacity(0), Square()
        data = capture_snapshot(self.scene(hidden, visible), 14, 8)
        self.assertEqual(len(data["objects"]), 1)

    def test_transparent_outline_is_visible_but_not_a_zero_width_stroke(self):
        self.assertGreater(visible_opacity(Square(fill_opacity=0)), 0)
        self.assertEqual(visible_opacity(Square(fill_opacity=0, stroke_width=0)), 0)

    def test_raw_bounds_preserve_clipped_and_offscreen_content(self):
        partial = Square().shift(7*RIGHT)
        outside = Square().shift(20*RIGHT)
        data = capture_snapshot(self.scene(partial, outside), 14, 8)
        self.assertEqual(len(data["offscreenObjects"]), 1)
        obj = data["objects"][0]
        self.assertGreater(obj["rawRegion"]["x"]+obj["rawRegion"]["width"], 1)
        self.assertLess(obj["region"]["width"], obj["rawRegion"]["width"])

    def test_ancestry_distinguishes_math_children_from_accidental_overlap(self):
        child = Square()
        data = capture_snapshot(self.scene(VGroup(child)), 14, 8)
        self.assertEqual(len(data["objects"]), 2)
        self.assertEqual(data["objects"][1]["parents"], [data["objects"][0]["id"]])
