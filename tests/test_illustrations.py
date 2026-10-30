import unittest
import numpy as np
from manim import RED
from algovis.core.illustrated import IllustrationImage,IllustratedItem


class IllustrationCopyTests(unittest.TestCase):
    def test_an_independently_animated_card_frame_stays_behind_its_contents(self):
        item=IllustratedItem(np.full((12,16,4),255,dtype=np.uint8),'item',1)
        self.assertLess(item.frame.z_index,item.image.z_index)
        self.assertLess(item.frame.z_index,item.display_name.z_index)

    def test_revealing_an_attribute_keeps_its_scene_label_role(self):
        from algovis import LessonTypography
        from algovis.layout import measured_font_size
        item=IllustratedItem(np.full((12,16,4),255,dtype=np.uint8),'item',1)
        item.apply_scene_typography(LessonTypography(),group='cards')
        updated=item.with_state(weight=1)
        self.assertEqual(updated.weight._algovis_type_role,'label')
        self.assertEqual(updated.weight.part('value')._algovis_type_role,'label')
        self.assertAlmostEqual(measured_font_size(updated.weight.part('value')),LessonTypography().label)
    def image(self):
        pixels=np.full((12,16,4),255,dtype=np.uint8)
        pixels[0,:,3]=128
        return IllustrationImage(pixels)

    def test_plans_share_pixels_but_opacity_cannot_change_another_plan(self):
        source=self.image();other=source.copy()
        self.assertIs(source.pixel_array,other.pixel_array)
        original=source.pixel_array.copy()
        other.set_opacity(.25)
        np.testing.assert_array_equal(source.pixel_array,original)
        self.assertIsNot(source.pixel_array,other.pixel_array)
        self.assertEqual(other.pixel_array[0,0,3],32)

    def test_a_color_override_detaches_from_the_source(self):
        source=self.image();other=source.copy();other.set_color(RED)
        np.testing.assert_array_equal(source.pixel_array[:,:,:3],255)
        self.assertFalse(np.array_equal(other.pixel_array,source.pixel_array))

    def test_alpha_interpolation_matches_the_native_pixel_result(self):
        source=self.image();start=source.copy().set_opacity(0);end=source.copy().set_opacity(.8)
        result=source.copy();expected=(start.pixel_array*.75+end.pixel_array*.25).astype(np.uint8)
        result.interpolate_color(start,end,.25)
        np.testing.assert_array_equal(result.pixel_array,expected)
        self.assertEqual(source.pixel_array[0,0,3],128)
