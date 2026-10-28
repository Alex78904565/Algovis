import unittest
from dataclasses import replace
from unittest.mock import patch

import numpy as np
from manim import LEFT, Rectangle, Scene, VGroup

import algovis
from algovis import frames


class SharedLessonFrameTests(unittest.TestCase):
    def test_one_style_change_reaches_every_proof_profile(self):
        standard = frames.DEFAULT_FRAME_STYLE
        changed = replace(standard, proof_content_left=-2.55,
                          proof_label_size=15, proof_label_left=-6.4)
        with patch.object(frames, 'DEFAULT_FRAME_STYLE', changed):
            for profile in frames.ProofFrame.PROFILES:
                frame = algovis.ProofFrame(profile)
                equation = Rectangle(width=3, height=.4)
                frame.place('claim', equation)
                self.assertAlmostEqual(equation.get_left()[0], changed.proof_content_left)
                self.assertAlmostEqual(frame.labels[1].get_left()[0], changed.proof_label_left)
                self.assertAlmostEqual(frame.labels[1].font_size, changed.proof_label_size)
                for glyph in frame.labels[1].family_members_with_points():
                    self.assertEqual(glyph.get_fill_color(), frame.theme.primary)

    def test_proof_placement_keeps_existing_objects_and_future_rows_out_of_scene(self):
        frame = algovis.ProofFrame('worked')
        equation = Rectangle(width=5, height=.8)
        width, height, children = equation.width, equation.height, tuple(equation.submobjects)
        scene = Scene()
        scene.add(equation)
        self.assertIs(frame.place('definitions', equation), equation)
        self.assertAlmostEqual(equation.width, width)
        self.assertAlmostEqual(equation.height, height)
        self.assertEqual(tuple(equation.submobjects), children)
        self.assertEqual(scene.mobjects, [equation])
        self.assertNotIn(frame.labels[0], scene.get_mobject_family_members())

    def test_proof_labels_cannot_silently_cross_the_divider(self):
        with self.assertRaisesRegex(ValueError, 'label column'):
            algovis.ProofFrame(style=replace(frames.DEFAULT_FRAME_STYLE, proof_divider_x=-6))

    def test_equation_profiles_share_the_same_left_anchor_without_shrinking(self):
        changed = replace(frames.DEFAULT_FRAME_STYLE, equation_left=-5.3)
        with patch.object(frames, 'DEFAULT_FRAME_STYLE', changed):
            for profile in frames.EquationFrame.PROFILES:
                frame = algovis.EquationFrame(profile)
                parts = [Rectangle(width=2, height=.6), Rectangle(width=3, height=.6)]
                line = frame.line(*parts)
                self.assertEqual(tuple(line.submobjects), tuple(parts))
                self.assertAlmostEqual(line.get_left()[0], -5.3)
                self.assertAlmostEqual(parts[0].width, 2)
                self.assertAlmostEqual(parts[1].get_left()[0]-parts[0].get_right()[0], changed.term_gap)
        oversized = Rectangle(width=30)
        with self.assertRaisesRegex(ValueError, 'type size'):
            algovis.EquationFrame().place('meaning', oversized)
        self.assertAlmostEqual(oversized.width, 30)

    def test_case_layout_reuses_the_original_rhs_and_respects_its_visibility(self):
        lhs = Rectangle(width=2, height=.5)
        first, second = Rectangle(width=4, height=.6), Rectangle(width=3, height=.6)
        second.set_opacity(0)
        rows = VGroup(first, second)
        cases = algovis.CaseEquation(lhs, rows)
        self.assertIs(cases.lhs, lhs)
        self.assertIs(cases.rows, rows)
        self.assertAlmostEqual(first.get_left()[0], second.get_left()[0])
        self.assertAlmostEqual(first.get_bottom()[1]-second.get_top()[1], frames.DEFAULT_FRAME_STYLE.case_gap)
        self.assertEqual(second.get_fill_opacity(), 0)
        self.assertEqual(cases.brace.get_color(), algovis.DEFAULT_THEME.foreground)

    def test_continuation_alignment_centers_the_complete_argument_and_preserves_parts(self):
        first = VGroup(Rectangle(width=2), Rectangle(width=.2)).arrange()
        continuation = VGroup(Rectangle(width=.2), Rectangle(width=5)).arrange().shift(LEFT*3)
        part = continuation[1]
        block = algovis.EquationFrame.align_continuation(first, continuation, first[1], continuation[0])
        self.assertAlmostEqual(first[1].get_x(), continuation[0].get_x())
        self.assertAlmostEqual(block.get_x(), 0)
        self.assertIs(continuation[1], part)
        self.assertAlmostEqual(part.width, 5)

    def test_panel_variants_share_geometry_and_preserve_meaning(self):
        changed = replace(frames.DEFAULT_FRAME_STYLE, panel_radius=.2, panel_stroke=3)
        with patch.object(frames, 'DEFAULT_FRAME_STYLE', changed):
            for variant in ('standard', 'quiet', 'miniature'):
                panel = algovis.PanelFrame(5, 3, variant=variant)
                self.assertAlmostEqual(panel.width, 5)
                self.assertAlmostEqual(panel.height, 3)
                self.assertAlmostEqual(panel.get_stroke_width(), 3)
                self.assertEqual(panel.get_stroke_color(), algovis.DEFAULT_THEME.primary)
                for glyph in panel.heading('A heading').family_members_with_points():
                    self.assertEqual(glyph.get_fill_color(), algovis.DEFAULT_THEME.foreground)

    def test_runtime_columns_share_one_offset(self):
        changed = replace(frames.DEFAULT_FRAME_STYLE, comparison_offset=3)
        frame = algovis.ComparisonFrame(style=changed)
        np.testing.assert_allclose(frame.anchor('right', 2), [3, 2, 0])
        np.testing.assert_allclose(frame.anchor('left', 2), [-3, 2, 0])
        self.assertAlmostEqual(frame.divider.get_x(), 0)
        with self.assertRaises(ValueError): frame.anchor('middle', 0)

    def test_public_proof_and_comparison_helpers_inherit_the_shared_defaults(self):
        changed = replace(frames.DEFAULT_FRAME_STYLE, proof_content_left=-2.55, panel_stroke=3.2)
        with patch.object(frames, 'DEFAULT_FRAME_STYLE', changed):
            proof = algovis.InductiveProof(measure='remaining items', claim='the value is optimal',
                base_case='no items remain', hypothesis='assume the smaller answer is correct',
                step='consider every choice', conclusion='therefore the claim holds')
            self.assertAlmostEqual(proof.rows[1][1].get_left()[0], -2.55)
            self.assertIs(proof.rows[1][0], proof.frame.labels_by_name['CLAIM'])
            comparison = algovis.RecurrenceComparison('f(n)=f(n-1)', 'f[n]=f[n-1]',
                'O(2^n)', 'O(n)', 'n=1,2,3')
            code = algovis.PseudocodePanel(['return value'])
            for panel in (comparison.recursive[0], comparison.array[0], code.background):
                self.assertIsInstance(panel, algovis.PanelFrame)
                self.assertAlmostEqual(panel.get_stroke_width(), 3.2)


if __name__ == '__main__':
    unittest.main()
