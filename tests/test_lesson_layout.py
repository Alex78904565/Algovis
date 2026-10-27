import unittest
from types import SimpleNamespace

from manim import Rectangle, Scene
from algovis import ColumnLayout, LessonStyle, SlideRegion
from algovis.review.inspection import capture_snapshot, typography_findings


class LessonLayoutTests(unittest.TestCase):
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
        self.assertEqual(len(findings[0]['objects']),2)
        second.scale(1/.8)
        self.assertEqual(typography_findings(capture_snapshot(scene,14,8)),[])

    def test_style_uses_semantic_colors_and_rejects_ad_hoc_overrides(self):
        style=LessonStyle()
        value=style.math('13',role='retained')
        self.assertEqual(value.get_color(),style.theme.success)
        with self.assertRaises(ValueError):style.math('x',font_size=25)
        with self.assertRaises(ValueError):style.text('x',color='red')


if __name__=='__main__':unittest.main()
