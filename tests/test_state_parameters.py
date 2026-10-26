import unittest

from algovis import BinaryStateVector, StateParameter
from manim import Scene, ManimColor


class StateParameterTests(unittest.TestCase):
    def test_setting_value_keeps_the_old_visible_object_until_played(self):
        parameter = StateParameter("v_1", [0, 1], 0)
        old = parameter.value_mobject
        parameter.scale(.6)
        height = old.height
        animation = parameter.set_value(1)
        self.assertIs(parameter.value_mobject, old)
        self.assertIn(old, parameter.submobjects)
        self.assertNotIn(animation.target_mobject, parameter.get_family())
        self.assertAlmostEqual(animation.target_mobject.height, height)
        self.assertEqual(parameter.value, 1)

    def test_boolean_flag_changes_its_text_and_style_together(self):
        vector = BinaryStateVector(["v_1"], [0], boolean_labels=True)
        parameter = vector.parameters[0]
        label = parameter.value_mobject
        self.assertEqual(label.tex_string, r"\mathrm{F}")
        animation = vector.set_bit(0, 1)
        self.assertEqual(label.tex_string, r"\mathrm{F}")
        self.assertEqual(parameter.box.get_fill_color(), ManimColor(vector.theme.surface))
        text_change, box_change = animation.animations
        self.assertEqual(text_change.target_mobject.tex_string, r"\mathrm{T}")
        self.assertEqual(box_change.target_mobject.get_fill_color(), ManimColor(vector.theme.success))
        scene = Scene()
        scene.add(vector)
        scene.add_mobjects_from_animations([animation])
        animation._setup_scene(scene)
        animation.begin()
        animation.finish()
        animation.clean_up_from_scene(scene)
        self.assertEqual(parameter.box.get_fill_color(), ManimColor(vector.theme.success))
        self.assertIs(parameter.value_mobject, label)
        self.assertNotIn(text_change.target_mobject, vector.get_family())

    def test_invalid_binary_state_is_rejected_instead_of_truncated(self):
        with self.assertRaises(ValueError):
            BinaryStateVector(["a", "b"], [0])
        with self.assertRaises(ValueError):
            BinaryStateVector(["a"], [2])


if __name__ == "__main__":
    unittest.main()
