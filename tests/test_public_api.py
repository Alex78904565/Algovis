import unittest

import algovis
from manim import BLUE, GREEN, RIGHT, Scene, Square, VGroup


class PublicApiTests(unittest.TestCase):
    def test_state_rows_reuse_the_same_cell_geometry_and_neutral_value_ink(self):
        import numpy as np
        row = algovis.StateRow([1, 13, 191])
        reference = algovis.StateCell(1)
        for cell in row:
            self.assertIs(cell[0], cell.box)
            self.assertIs(cell[1], cell.label)
            self.assertAlmostEqual(cell.box.width, reference.box.width)
            self.assertAlmostEqual(cell.box.height, reference.box.height)
            self.assertEqual(cell.box.get_stroke_color(), cell.theme.primary)
            self.assertEqual(cell.label.get_color(), cell.theme.foreground)
            np.testing.assert_allclose(cell.label.get_center(), cell.box.get_center(), atol=1e-10)
        self.assertAlmostEqual(row[1].get_left()[0]-row[0].get_right()[0], .42)
        with self.assertRaisesRegex(ValueError, 'reserve a wider cell'):
            algovis.StateCell('12345678901234567890')

    def test_selected_definition_terms_can_land_in_an_explicit_compact_layout(self):
        import numpy as np
        source = VGroup(Square(), Square().shift(5 * RIGHT))
        source[0].tex_string, source[1].tex_string = 'a', '=b'
        destination = VGroup(Square(), Square().shift(1.4 * RIGHT)).shift(3 * RIGHT)
        destination[0].tex_string, destination[1].tex_string = 'a', '=b'
        children = tuple(destination.submobjects)
        points = destination.get_all_points().copy()
        animation = algovis.ApplyDefinition(
            source, None, destination, preserve_destination_layout=True)
        self.assertEqual(tuple(destination.submobjects), children)
        np.testing.assert_allclose(destination.get_all_points(), points)
        scene = Scene()
        scene.add(source)
        scene.add_mobjects_from_animations([animation])
        animation._setup_scene(scene)
        animation.begin()
        animation.interpolate(.35)
        self.assertAlmostEqual(animation.traveller[1].get_x()-animation.traveller[0].get_x(), 5)
        animation.finish()
        animation.clean_up_from_scene(scene)
        np.testing.assert_allclose(destination.get_all_points(), points)
        self.assertIn(destination, scene.get_mobject_family_members())

    def test_performance_evaluation_overrides_computed_runtime_status(self):
        comparisons = (
            algovis.RecurrenceComparison(
                'f(n)=f(n-1)', 'f[n]=f[n-1]', 'O(2^n)', 'O(n)', 'n=1,2,3'),
            algovis.AlgorithmComparison(
                ['return f(n-1)'], ['return f[n-1]'], 'O(2^n)', 'O(n)'),
        )
        for comparison in comparisons:
            for runtime,color in ((comparison.naive_runtime,comparison.theme.danger),
                                  (comparison.optimized_runtime,comparison.theme.success)):
                for glyph in runtime.family_members_with_points():
                    self.assertEqual(glyph.get_fill_color(), color)

    def test_bit_length_limitation_overrides_its_valid_derivation(self):
        explanation = algovis.BitLengthRuntime()
        for runtime in (explanation.runtimes[0], explanation.runtimes[2]):
            for glyph in runtime.family_members_with_points():
                self.assertEqual(glyph.get_fill_color(), explanation.theme.success)
        for negative in (explanation.rewritten,explanation.warning):
            for glyph in negative.family_members_with_points():
                self.assertEqual(glyph.get_fill_color(), explanation.theme.danger)

    def test_good_bad_evaluation_wins_over_all_other_roles_in_any_order(self):
        theme=algovis.DEFAULT_THEME
        for role in ('retained','success','operation','current','structure','muted','neutral'):
            for evaluation,color in (('good',theme.success),('bad',theme.danger)):
                self.assertEqual(theme.role_color(role,evaluation),color)
                self.assertEqual(theme.role_color(evaluation,role),color)

    def test_lower_priority_roles_are_resolved_by_the_same_hierarchy(self):
        theme=algovis.DEFAULT_THEME
        self.assertEqual(theme.role_color('current','operation','retained'),theme.success)
        self.assertEqual(theme.role_color('neutral','current','operation'),theme.accent)
        self.assertEqual(theme.role_color('muted','structure'),theme.primary)
        self.assertEqual(theme.role_color('neutral','muted'),theme.muted)

    def test_conflicting_evaluations_are_not_decided_by_argument_order(self):
        theme=algovis.DEFAULT_THEME
        for roles in (('good','bad'),('danger','good'),('good','repeated')):
            with self.assertRaisesRegex(ValueError,'Conflicting'):
                theme.role_color(*roles)
        with self.assertRaisesRegex(ValueError,'Unknown'):
            theme.role_color('good','misspelled')

    def test_comparison_headings_do_not_use_stored_answer_color(self):
        comparison=algovis.RecurrenceComparison(
            'f(n)=f(n-1)', 'f[n]=f[n-1]', 'O(2^n)', 'O(n)', 'n=1,2,3')
        for panel in (comparison.recursive,comparison.array):
            for glyph in panel[1].family_members_with_points():
                self.assertEqual(glyph.get_fill_color(),comparison.theme.foreground)
            self.assertEqual(panel[0].get_stroke_color(),comparison.theme.primary)

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

    def test_wipe_group_finishes_before_transition_replacement_starts(self):
        from manim import AnimationGroup, FadeIn, FadeOut, Succession
        scene = object.__new__(algovis.SlideScene)
        first, second, target = Square(), Square().shift(RIGHT), Square()
        scene.mobjects = [first, second]
        captured = []
        scene.play = lambda animation, **kwargs: captured.append((animation, kwargs))
        exits = AnimationGroup(scene.wipe(first), AnimationGroup(FadeOut(second)))
        scene.transition(exits, FadeIn(target), run_time=.8)
        animation, kwargs = captured[0]
        self.assertIsInstance(animation, Succession)
        outgoing, incoming = animation.anims_with_timings
        self.assertLessEqual(outgoing['end'], incoming['start'])
        self.assertIs(outgoing['anim'].animations[0], exits)
        self.assertEqual(kwargs['run_time'], .8)

    def test_transition_preserves_mixed_authored_sequence(self):
        from manim import FadeIn, FadeOut, Succession
        scene = object.__new__(algovis.SlideScene)
        source, target = Square(), Square()
        scene.mobjects = [source]
        captured = []
        scene.play = lambda *animations, **kwargs: captured.extend(animations)
        sequence = Succession(FadeOut(source), FadeIn(target))
        scene.transition(sequence, run_time=.8)
        self.assertEqual(captured, [sequence])

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
        for card in comparison.cards:
            heading_paint={part.get_fill_color().to_hex()
                           for part in card.heading.family_members_with_points()}
            self.assertEqual(heading_paint,{comparison.theme.foreground.to_hex()})
            self.assertEqual(card[0].get_stroke_color(),comparison.theme.primary)
            self.assertEqual(card.equation.get_color(),comparison.theme.primary)
        self.assertEqual(comparison.original.bound.get_color(),comparison.theme.primary)
        self.assertEqual(comparison.original.runtime.get_color(),comparison.theme.success)

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

    def test_definition_transfer_can_route_around_intervening_rows(self):
        import numpy as np
        from manim import UP, DOWN
        scene = Scene()
        definition = VGroup(Square(side_length=.3), Square(side_length=.6).shift(RIGHT))
        result = definition.copy().shift(3 * DOWN)
        scene.add(definition)
        via = [4 * RIGHT + UP, 4 * RIGHT + 3 * DOWN]
        animation = algovis.ApplyDefinition(definition, None, result, via=via)
        scene.add_mobjects_from_animations([animation])
        animation._setup_scene(scene)
        animation.begin()
        for alpha, expected in ((.70/3, via[0]), (.70*2/3, via[1])):
            animation.interpolate(alpha)
            np.testing.assert_allclose(animation.traveller.get_center(), expected, atol=1e-7)
            np.testing.assert_allclose(
                animation.traveller[1].get_center()-animation.traveller[0].get_center(),
                definition[1].get_center()-definition[0].get_center(), atol=1e-7)
        animation.finish()
        animation.clean_up_from_scene(scene)
        np.testing.assert_allclose(result.get_center(), definition.get_center()+3 * DOWN)

    def test_definition_transfer_uses_source_position_when_its_turn_begins(self):
        import numpy as np
        from manim import LEFT, UP
        definition = VGroup(Square(side_length=.3), Square(side_length=.7).shift(RIGHT))
        result = Square().shift(4 * RIGHT)
        animation = algovis.ApplyDefinition(definition, None, result)
        # Stand in for an earlier layout move in a composed Succession.
        definition.scale(.6).shift(2 * UP + 3 * LEFT)
        source_points = definition.get_all_points().copy()
        scene = Scene()
        scene.add(definition)
        scene.add_mobjects_from_animations([animation])
        animation._setup_scene(scene)
        animation.begin()
        animation.interpolate(0)
        np.testing.assert_allclose(animation.traveller.get_all_points(), source_points, atol=1e-7)
        animation.interpolate(.35)
        np.testing.assert_allclose(
            animation.traveller[1].get_center() - animation.traveller[0].get_center(),
            definition[1].get_center() - definition[0].get_center(), atol=1e-7)
        animation.finish()
        animation.clean_up_from_scene(scene)
        np.testing.assert_allclose(definition.get_all_points(), source_points, atol=1e-7)

    def test_delayed_definition_copy_is_absent_until_its_turn(self):
        import numpy as np
        from manim import LEFT, UP, Succession
        definition = VGroup(Square(side_length=.3), Square(side_length=.7).shift(RIGHT))
        result = Square().shift(4 * RIGHT)
        transfer = algovis.ApplyDefinition(definition, None, result, run_time=1)
        sequence = Succession(
            definition.animate(run_time=1).scale(.6).shift(2 * UP + 3 * LEFT),
            transfer,
        )
        scene = Scene()
        scene.add(definition)
        scene.add_mobjects_from_animations([sequence])
        sequence._setup_scene(scene)
        sequence.begin()
        sequence.interpolate(.25)
        self.assertNotIn(transfer.traveller, scene.get_mobject_family_members())

        sequence.interpolate(.5)
        self.assertIn(transfer.traveller, scene.get_mobject_family_members())
        np.testing.assert_allclose(transfer.traveller.get_all_points(), definition.get_all_points())
        sequence.finish()
        sequence.clean_up_from_scene(scene)
        self.assertIn(result, scene.get_mobject_family_members())
        self.assertNotIn(transfer.traveller, scene.get_mobject_family_members())

    def test_definition_cleanup_does_not_revive_a_later_replaced_formula(self):
        definition, result = Square(), Square().shift(4 * RIGHT)
        scene = Scene()
        scene.add(definition)
        transfer = algovis.ApplyDefinition(definition, None, result)
        transfer._setup_scene(scene)
        transfer.begin()
        transfer.finish()
        transfer.clean_up_from_scene(scene)
        self.assertIn(result, scene.get_mobject_family_members())
        # A later step replaces this adopted result. An enclosing Succession
        # then repeats cleanup of its earlier children.
        replacement = Square().shift(2 * RIGHT)
        scene.remove(*result.get_family())
        scene.add(replacement)
        transfer.clean_up_from_scene(scene)
        self.assertNotIn(result, scene.get_mobject_family_members())
        self.assertIn(replacement, scene.get_mobject_family_members())

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
        traveller = animation.travelling_formula
        self.assertLess(traveller[0].get_x(), traveller[1].get_x())

    def test_identical_formula_preserves_requested_destination_color(self):
        definition = VGroup(Square(color=GREEN), Square(color=GREEN).shift(2 * RIGHT))
        definition.tex_string = "k(k+1)/2"
        result = VGroup(Square(color=BLUE)).shift(4 * RIGHT)
        result.tex_string = "k(k+1)/2"
        algovis.ApplyDefinition(definition, None, result)
        self.assertTrue(all(part.get_color() == BLUE for part in result.family_members_with_points()))
        self.assertTrue(all(part.get_color() == GREEN for part in definition.family_members_with_points()))

    def test_definition_glyphs_travel_rigidly_before_local_substitution(self):
        import numpy as np
        source = VGroup(Square(side_length=.3), Square(side_length=.7).shift(RIGHT))
        destination = Square().shift(4 * RIGHT)
        scene = Scene()
        scene.camera.background_color = BLUE
        scene.add(source)
        animation = algovis.ApplyDefinition(source, None, destination)
        original_delta = source[1].get_center() - source[0].get_center()
        scene.add_mobjects_from_animations([animation])
        animation._setup_scene(scene)
        animation.begin()
        animation.interpolate(.35)
        travelling = animation.travelling_formula
        np.testing.assert_allclose(travelling[1].get_center()-travelling[0].get_center(),
                                   original_delta, atol=1e-7)
        self.assertIs(animation.traveller, travelling)
        self.assertEqual(len(travelling.submobjects), len(source.submobjects))
        self.assertTrue(all(obj.__class__.__name__ != "BackgroundRectangle"
                            for obj in travelling.get_family()))
        self.assertNotIn(destination, scene.get_mobject_family_members())

    def test_definition_arrival_has_no_blank_interval_or_shape_change_on_adoption(self):
        import numpy as np
        source = VGroup(Square(side_length=.3), Square(side_length=.7).shift(RIGHT))
        destination = VGroup(Square(side_length=.5), Square(side_length=.4).shift(RIGHT))
        destination.shift(4 * RIGHT)
        scene = Scene()
        scene.add(source)
        animation = algovis.ApplyDefinition(source, None, destination)
        scene.add_mobjects_from_animations([animation])
        animation._setup_scene(scene)
        animation.begin()
        for progress in (.68, .70, .75, .85, .99):
            animation.interpolate(progress)
            self.assertIn(animation.traveller, scene.get_mobject_family_members())
            self.assertTrue(all(max(obj.get_fill_opacity(), obj.get_stroke_opacity()) > .99
                                for obj in animation.traveller.family_members_with_points()))
        animation.finish()
        painted = animation.traveller.get_all_points().copy()
        animation.clean_up_from_scene(scene)
        np.testing.assert_allclose(destination.get_all_points(), painted, atol=1e-7)
        self.assertIn(source, scene.get_mobject_family_members())
        self.assertNotIn(animation.traveller, scene.get_mobject_family_members())

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
