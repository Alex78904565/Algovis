import unittest

import algovis
from manim import BLUE, GREEN, RIGHT, Scene, Square, VGroup


class PublicApiTests(unittest.TestCase):
    def test_clear_before_reveal_finishes_exit_before_replacement_starts(self):
        from manim import FadeIn, FadeOut
        scene = object.__new__(algovis.SlideScene)
        source = Square()
        scene.mobjects = [source]
        captured = []
        scene.play = lambda animation, **kwargs: captured.append((animation, kwargs))
        scene.transition(FadeOut(source), FadeIn(Square()), run_time=0.7)
        animation, kwargs = captured[0]
        first, second = animation.anims_with_timings
        self.assertLessEqual(first["end"], second["start"])
        self.assertEqual(kwargs["run_time"], 0.7)

    def test_cleanup_animation_cannot_reintroduce_absent_children(self):
        from manim import FadeOut
        scene = object.__new__(algovis.SlideScene)
        present, absent = Square(), Square().shift(RIGHT)
        scene.mobjects = [present]
        fade = FadeOut(VGroup(present, absent))
        filtered = scene._filter_cleanup_animations((fade, FadeOut(absent)))
        self.assertEqual(filtered, (fade,))
        self.assertIs(fade.mobject, present)

    def test_cleanup_in_a_sequence_is_not_pruned_before_its_reveal(self):
        from manim import FadeIn, FadeOut, Succession
        scene = object.__new__(algovis.SlideScene)
        scene.mobjects = []
        value = Square()
        sequence = Succession(FadeIn(value), FadeOut(value))
        self.assertEqual(scene._filter_cleanup_animations((sequence,)), (sequence,))

    def test_partial_group_cleanup_keeps_all_present_children(self):
        from manim import FadeOut
        scene = object.__new__(algovis.SlideScene)
        first, second, absent = Square(), Square(), Square()
        scene.mobjects = [first, second]
        fade = FadeOut(VGroup(first, second, absent))
        scene._filter_cleanup_animations((fade,))
        self.assertEqual(list(fade.mobject.submobjects), [first, second])

    def test_whole_content_replacement_does_not_crossfade_text(self):
        animation = algovis.ReplaceContent(Square(), Square())
        outgoing, incoming = animation.anims_with_timings
        self.assertLessEqual(outgoing["end"], incoming["start"])

    def test_state_definition_can_precede_its_domain_and_runtime(self):
        comparison = algovis.StateReframing(
            original_tex="f(i,w)", alternate_tex="f(i,v)",
            original_meaning="maximum value", alternate_meaning="minimum weight",
            original_bound="0\\le w\\le C", original_runtime="O(nC)",
            alternate_bound=None, alternate_runtime=None,
        )
        self.assertIsNone(comparison.alternate.bound)
        self.assertIsNone(comparison.alternate.runtime)
        self.assertIsNotNone(comparison.alternate.meaning)

    def test_attention_pulse_preserves_mixed_semantic_colors(self):
        group = VGroup(Square(color=GREEN), Square(color=BLUE).shift(3*RIGHT))
        colors = [child.get_color() for child in group]
        animation = algovis.Pulse(group)
        animation.begin()
        animation.interpolate(.5)
        self.assertEqual([child.get_color() for child in group], colors)
        animation.finish()
    def test_version_is_exposed(self):
        self.assertEqual(algovis.__version__, "0.1.0")

    def test_primary_authoring_components_are_exposed(self):
        for name in (
            "SlideScene",
            "NarrationTrack",
            "RecursiveTree",
            "DPTable",
            "BellmanDerivation",
            "InductiveProof",
            "RecursionMemoComparison",
            "Storyboard",
            "StoryAnimation",
            "AnimationBeat",
            "ApplyDefinition",
        ):
            self.assertTrue(hasattr(algovis, name), name)

    def test_recursive_tree_supports_subtree_collapse(self):
        self.assertTrue(hasattr(algovis.RecursiveTree, "collapse_to_backbone"))
        self.assertTrue(hasattr(
            algovis.RecursiveTree,
            "get_backbone_collapse_animations",
        ))
        self.assertTrue(hasattr(algovis.RecursiveTree, "set_state_colors"))

    def test_theme_resolves_storyboard_roles(self):
        self.assertEqual(
            algovis.DEFAULT_THEME.role_color("current"),
            algovis.DEFAULT_THEME.primary,
        )
        self.assertEqual(
            algovis.DEFAULT_THEME.role_color("operation"),
            algovis.DEFAULT_THEME.accent,
        )

    def test_present_mobjects_filters_absent_cleanup_targets(self):
        scene = object.__new__(algovis.SlideScene)
        visible = Square()
        absent = Square()
        scene.mobjects = [VGroup(visible)]

        self.assertEqual(scene.present_mobjects(visible, absent), (visible,))

    def test_definition_transfer_keeps_source_and_unrelated_terms(self):
        scene = Scene()
        definition = Square(color=GREEN).shift(-3 * RIGHT)
        application = Square(color=BLUE)
        untouched = Square().shift(3 * RIGHT)
        result = Square(side_length=1, color=GREEN).move_to(application)
        source_points = definition.get_all_points().copy()
        scene.add(definition, application, untouched)
        animation = algovis.ApplyDefinition(definition, application, result)
        scene.add_mobjects_from_animations([animation])
        animation._setup_scene(scene)
        animation.begin()
        animation.interpolate(.5)
        self.assertTrue((definition.get_all_points() == source_points).all())
        animation.finish()
        animation.clean_up_from_scene(scene)
        visible = scene.get_mobject_family_members()
        self.assertIn(definition, visible)
        self.assertIn(untouched, visible)
        self.assertIn(result, visible)
        self.assertNotIn(application, visible)

    def test_definition_transfer_can_fill_a_blank_position(self):
        definition, result = Square(), Square().shift(2 * RIGHT)
        animation = algovis.ApplyDefinition(definition, None, result)
        self.assertEqual(len(animation.animations), 1)

    def test_review_labels_follow_transformed_content_without_changing_tex(self):
        from manim import Transform
        source, target = VGroup(Square()), VGroup(Square())
        source.tex_string = "old expression"
        target.tex_string = "new expression"
        algovis.SlideScene._refresh_review_labels([Transform(source, target)])
        self.assertEqual(source._algovis_label, "new expression")
        self.assertEqual(source.tex_string, "old expression")

    def test_identical_formula_keeps_its_symbol_groups_during_transfer(self):
        # Equivalent text with different grouping used to match the zero in
        # f(0) to the zero after '='. Use asymmetric stand-ins for the glyphs
        # so the identity-preserving geometry can be tested without LaTeX.
        left = VGroup(Square(side_length=.3)).shift(-RIGHT)
        left.tex_string = "f(0)"
        right = VGroup(Square(side_length=.5)).shift(RIGHT)
        right.tex_string = "=0"
        definition = VGroup(left, right)
        result = VGroup(Square(side_length=.8)).shift(4 * RIGHT)
        result.tex_string = "f(0)=0"
        original = definition.get_all_points().copy()
        animation = algovis.ApplyDefinition(definition, None, result)
        self.assertEqual(len(result.submobjects), 2)
        self.assertLess(result[0].get_x(), result[1].get_x())
        self.assertTrue((definition.get_all_points() == original).all())
        scene = Scene()
        scene.add(definition)
        scene.add_mobjects_from_animations([animation])
        animation._setup_scene(scene)
        animation.begin()
        animation.interpolate(.5)
        traveller = animation.animations[0].mobject
        self.assertLess(traveller[0].get_x(), traveller[1].get_x())

    def test_definition_destination_is_not_visible_under_the_travelling_copy(self):
        scene = Scene()
        definition, result = Square(), Square().shift(2 * RIGHT)
        scene.add(definition, VGroup(result))
        animation = algovis.ApplyDefinition(definition, None, result)
        scene.add_mobjects_from_animations([animation])
        animation._setup_scene(scene)
        self.assertNotIn(result, scene.get_mobject_family_members())
        animation.begin()
        animation.finish()
        animation.clean_up_from_scene(scene)
        self.assertIn(result, scene.get_mobject_family_members())

    def test_cleanup_finds_present_children_of_an_unregistered_wrapper(self):
        scene = object.__new__(algovis.SlideScene)
        visible, absent = Square(), Square()
        wrapper = VGroup(visible, absent)
        scene.mobjects = [visible]
        self.assertEqual(scene.present_mobjects(wrapper), (visible,))

    def test_cleanup_does_not_animate_parent_and_child_twice(self):
        scene = object.__new__(algovis.SlideScene)
        child = Square()
        parent = VGroup(child)
        scene.mobjects = [parent]
        self.assertEqual(scene.present_mobjects(child, parent, child), (parent,))

    def test_definition_transfer_has_one_semantic_timeline_bar(self):
        scene = object.__new__(algovis.SlideScene)
        scene._review_object_ids = {}
        scene._review_animations = []
        animation = algovis.ApplyDefinition(Square(), None, Square())
        scene._append_review_animation(animation, 2, 3.2, 0, "1")
        self.assertEqual(len(scene._review_animations), 1)
        self.assertEqual(scene._review_animations[0]["kind"], "ApplyDefinition")
        self.assertEqual(scene._review_animations[0]["start"], 2)
        self.assertEqual(scene._review_animations[0]["end"], 3.2)

    def test_selected_svg_terms_can_keep_readable_definition_labels(self):
        scene = object.__new__(algovis.SlideScene)
        scene._review_object_ids = {}
        scene._review_animations = []
        animation = algovis.ApplyDefinition(
            VGroup(Square()), None, VGroup(Square()),
            definition_label="f(i,w)", result_label="f(i+1,w)",
        )
        scene._append_review_animation(animation, 0, 1, 0, "1")
        self.assertEqual(scene._review_object_label(animation.result), "f(i+1,w)")
        self.assertIn("f(i,w)", scene._review_animations[0]["label"])


if __name__ == "__main__":
    unittest.main()
