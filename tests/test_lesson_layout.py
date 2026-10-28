import unittest
from types import SimpleNamespace

from manim import Rectangle, Scene
from algovis import ColumnLayout, LessonStyle, SlideRegion
from algovis.review.inspection import capture_snapshot, typography_findings, alignment_findings


class LessonLayoutTests(unittest.TestCase):
    def test_centered_column_balances_completed_content_without_centering_each_row(self):
        region=SlideRegion((2,0,0),12,6)
        short,long=Rectangle(width=3,height=.5),Rectangle(width=7,height=.5)
        column=ColumnLayout(region,padding=.5,content_width=max(short.width,long.width))
        column.add('short',short);column.add('long',long)
        self.assertAlmostEqual(short.get_left()[0],long.get_left()[0])
        self.assertAlmostEqual(long.get_center()[0],region.center[0])
        self.assertAlmostEqual(short.width,3)
        self.assertAlmostEqual(long.width,7)
        self.assertAlmostEqual(short.get_left()[0]-(region.center[0]-region.width/2),
                               region.center[0]+region.width/2-long.get_right()[0])

    def test_centered_column_rejects_invalid_or_oversized_content_width(self):
        region=SlideRegion((0,0,0),8,6)
        for width in (0,-1,float('nan'),float('inf'),7.1):
            with self.subTest(width=width),self.assertRaisesRegex(ValueError,'content width'):
                ColumnLayout(region,padding=.5,content_width=width)

    def test_identical_copy_does_not_register_a_smaller_supporting_condition(self):
        from manim import MathTex, VGroup
        from algovis import ApplyDefinition
        style=LessonStyle()
        source=VGroup(style.math('f(i,w)',peers='reference'),
                      MathTex(r'w\le C').scale(.5))
        target=source.copy()
        style.watch('application',target[0])
        ApplyDefinition(source,None,target)
        self.assertEqual(target[0]._algovis_typography_group,'application')
        self.assertFalse(any(hasattr(part,'_algovis_typography_group')
                             for part in target[1].get_family()))

    def test_identical_selected_definition_preserves_rigid_copy_structure(self):
        from algovis import ApplyDefinition
        style=LessonStyle()
        source=style.math(r'\#\text{ operations}',r'\ge',peers='proof')
        destination=style.math(r'\#\text{ operations}',peers='proof')
        transfer=ApplyDefinition(source[0],None,destination)
        self.assertEqual(len(destination.submobjects),len(source[0].submobjects))
        scene=object.__new__(Scene);scene.mobjects=[source,destination]
        scene._review_object_ids={};scene._review_next_object_id=1
        scene._review_object_label=lambda obj:getattr(obj,'tex_string','')
        scene.renderer=SimpleNamespace(time=2)
        self.assertEqual(typography_findings(capture_snapshot(scene,14,8)),[])

    def test_partial_fraction_substitution_retains_surrounding_type_size(self):
        from manim import Transform
        from algovis import SlideScene
        style=LessonStyle()
        source=style.math('f(k)','=', 'k',peers='proof')
        target=style.math(r'{k(k+1)\over2}',peers='proof')
        animation=Transform(source[2],target)
        animation.begin();animation.interpolate(1);animation.finish()
        SlideScene._refresh_review_labels((animation,))
        scene=object.__new__(Scene);scene.mobjects=[source]
        scene._review_object_ids={};scene._review_next_object_id=1
        scene._review_object_label=lambda obj:getattr(obj,'tex_string','')
        scene.renderer=SimpleNamespace(time=2)
        self.assertEqual(typography_findings(capture_snapshot(scene,14,8)),[])

    def test_identical_transfer_preserves_destination_group_and_absent_contract(self):
        from manim import MathTex, VGroup
        from algovis import ApplyDefinition
        style=LessonStyle()
        source=style.math('f','(', 'i',')',peers='reference')
        answer=style.watch('answer',VGroup(*source.copy()).scale(1.2))
        ApplyDefinition(VGroup(*source),None,answer)
        self.assertEqual({part._algovis_typography_group for part in answer
                          if hasattr(part,'_algovis_typography_group')},{'answer'})
        from algovis.review.inspection import measured_font_size
        self.assertAlmostEqual(measured_font_size(answer[0]),33.6*1.2)
        footer=MathTex('f(i)').scale(.5)
        ApplyDefinition(source,None,footer)
        self.assertFalse(any(hasattr(part,'_algovis_typography_group')
                             for part in footer.get_family()))

    def test_math_like_matches_type_size_rather_than_fraction_height(self):
        style=LessonStyle()
        reference=style.math('f(k)',peers='reference').scale(.8)
        result=style.math_like(reference,r'{k(k+1)\over2}',peers='reference')
        self.assertAlmostEqual(result.font_size,reference.font_size)
        self.assertGreater(result.height,reference.height)

    def test_a_pulse_does_not_change_the_recorded_type_size(self):
        from algovis import SlideScene
        from manim import Indicate
        from algovis.review.inspection import measured_font_size
        value=LessonStyle().math('f(k)',peers='formula')
        pulse=Indicate(value,scale_factor=1.08)
        pulse.begin();pulse.interpolate(1);pulse.finish()
        SlideScene._refresh_review_labels((pulse,))
        self.assertAlmostEqual(measured_font_size(value),33.6)

    def test_a_copy_transfer_keeps_the_destinations_type_size_and_label(self):
        from manim import TransformFromCopy
        from algovis import SlideScene
        from algovis.review.inspection import measured_font_size
        style=LessonStyle()
        source=style.math('n',peers='source').scale(.7)
        target=style.math('191',peers='target')
        transfer=TransformFromCopy(source,target)
        transfer.begin();transfer.interpolate(1);transfer.finish()
        SlideScene._refresh_review_labels((transfer,))
        self.assertAlmostEqual(measured_font_size(target),33.6)
        self.assertFalse(hasattr(target,'_algovis_label'))

    def test_a_substituted_fraction_does_not_enlarge_peer_font_measurement(self):
        from manim import Transform
        from algovis import SlideScene
        style=LessonStyle()
        source=style.math('f(k)','=', 'k',peers='proof')
        target=style.math('f(k)','=',r'{k(k+1)\over2}',peers='proof')
        animation=Transform(source,target)
        animation.begin();animation.interpolate(1);animation.finish()
        SlideScene._refresh_review_labels((animation,))
        scene=object.__new__(Scene);scene.mobjects=[source,target]
        scene._review_object_ids={};scene._review_next_object_id=1
        scene._review_object_label=lambda obj:getattr(obj,'tex_string','')
        scene.renderer=SimpleNamespace(time=2)
        self.assertEqual(typography_findings(capture_snapshot(scene,14,8)),[])
        source.scale(.8)
        self.assertTrue(typography_findings(capture_snapshot(scene,14,8)))

    def test_existing_rows_are_watched_without_resizing_them(self):
        from manim import MathTex, Text, VGroup
        style=LessonStyle();formula=MathTex('f(n)').scale(.7)
        heading=Text('definition',font_size=20);row=VGroup(heading,formula)
        before=formula.width
        self.assertIs(style.watch('definition',row),row)
        self.assertEqual(formula._algovis_typography_group,'definition')
        self.assertFalse(hasattr(heading,'_algovis_typography_group'))
        self.assertAlmostEqual(formula.width,before)

    def test_travelling_copies_do_not_join_an_alignment_contract(self):
        from manim import VGroup, RIGHT
        first,second=Rectangle(width=3,height=1),Rectangle(width=5,height=1)
        first.shift(RIGHT);second.align_to(first,[-1,0,0])
        LessonStyle.align_rows('definitions',first,second)
        travelling=first.copy().shift(RIGHT*3)
        scene=object.__new__(Scene);scene.mobjects=[first,second,travelling]
        scene._review_object_ids={};scene._review_next_object_id=1
        scene._review_object_label=lambda obj:'row'
        scene.renderer=SimpleNamespace(time=2)
        self.assertEqual(alignment_findings(capture_snapshot(scene,14,8)),[])
        second.shift(RIGHT)
        self.assertEqual(alignment_findings(capture_snapshot(scene,14,8))[0]['kind'],
                         'declared_left_edge_mismatch')

    def test_nested_columns_share_parent_bounds_and_requested_gutter(self):
        parent = SlideRegion((1, 2, 0), 10, 6)
        left, right = parent.split_columns(1, 3, gutter=2)
        self.assertAlmostEqual(left.width, 2)
        self.assertAlmostEqual(right.width, 6)
        self.assertAlmostEqual(right.center[0]-right.width/2-(left.center[0]+left.width/2), 2)
        self.assertEqual(left.center[1:], parent.center[1:])
        self.assertAlmostEqual(left.center[0]-left.width/2, -4)
        self.assertAlmostEqual(right.center[0]+right.width/2, 6)

    def test_column_keeps_left_edges_and_sizes_without_scene_ownership(self):
        column = ColumnLayout(SlideRegion((0,0,0),8,6), gap=.4)
        first, second = Rectangle(width=3,height=1), Rectangle(width=6,height=.5)
        column.add('meaning',first);column.add('rule',second)
        self.assertAlmostEqual(first.get_left()[0],second.get_left()[0])
        self.assertAlmostEqual(first.get_bottom()[1]-second.get_top()[1],.4)
        self.assertAlmostEqual(first.width,3)
        self.assertAlmostEqual(second.width,6)
        self.assertEqual(len(first.submobjects),0)

    def test_overflow_raises_without_shrinking_or_consuming_a_row(self):
        column = ColumnLayout(SlideRegion((0,0,0),4,3))
        too_wide = Rectangle(width=5,height=1)
        with self.assertRaisesRegex(ValueError,'width'):column.add('rule',too_wide)
        self.assertAlmostEqual(too_wide.width,5)
        column.add('rule',Rectangle(width=3,height=1))
        with self.assertRaisesRegex(ValueError,'height'):column.reserve('proof',4)

    def test_replacement_keeps_its_slot_and_does_not_move_other_rows(self):
        column = ColumnLayout(SlideRegion((0,0,0),8,6))
        first, second = Rectangle(width=3,height=1), Rectangle(width=3,height=1)
        column.add('rule',first);column.add('base',second)
        old_second = second.get_center().copy()
        target = column.place('rule',Rectangle(width=6,height=.8))
        self.assertAlmostEqual(target.get_left()[0],first.get_left()[0])
        self.assertAlmostEqual(target.get_top()[1],first.get_top()[1])
        self.assertTrue((second.get_center()==old_second).all())

    def test_bad_weights_and_duplicate_slots_are_rejected(self):
        region=SlideRegion((0,0,0),8,6)
        with self.assertRaises(ValueError):region.split_columns(1,0)
        with self.assertRaises(ValueError):region.split_columns(1,1,gutter=9)
        column=ColumnLayout(region);column.reserve('rule',1)
        with self.assertRaises(ValueError):column.reserve('rule',1)

    def test_peer_type_sizes_are_measured_after_scaling(self):
        style=LessonStyle()
        first=style.math('f(n)',peers='recurrence')
        second=style.math('f(7)',peers='recurrence').scale(.8)
        note=style.text('known result',type_role='note',peers='recurrence')
        scene=object.__new__(Scene);scene.mobjects=[first,second,note]
        scene._review_object_ids={};scene._review_next_object_id=1
        scene._review_object_label=lambda obj:getattr(obj,'tex_string',getattr(obj,'text',''))
        scene.renderer=SimpleNamespace(time=2)
        snapshot=capture_snapshot(scene,14,8)
        findings=typography_findings(snapshot)
        self.assertEqual(len(findings),1)
        self.assertEqual(findings[0]['typeRole'],'equation')
        self.assertEqual({o['fontSize'] for o in findings[0]['objects']},{33.6,26.88})
        second.scale(1/.8)
        self.assertEqual(typography_findings(capture_snapshot(scene,14,8)),[])

    def test_style_uses_semantic_colors_and_rejects_ad_hoc_overrides(self):
        style=LessonStyle()
        value=style.math('13',role='retained')
        self.assertEqual(value.get_color(),style.theme.success)
        with self.assertRaises(ValueError):style.math('x',font_size=25)
        with self.assertRaises(ValueError):style.text('x',color='red')


if __name__=='__main__':unittest.main()
