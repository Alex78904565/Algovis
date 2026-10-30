import unittest
import numpy as np
from manim import Rectangle, Scene, Text
from algovis import ColumnSlide, FitPolicy, MathRow, ProofSlide, SplitSlide


class AutomaticFittingTests(unittest.TestCase):
    def wide(self, view, slot='body'):
        width=view._text_width(slot)
        return Rectangle(width=width/.85,height=.5)

    def test_related_columns_scale_together_and_remain_left_aligned(self):
        view=SplitSlide()
        view.add('diagram',self.wide(view,'left'))
        view.add('left',Text('Left explanation',font_size=26))
        view.add('right',Text('Right explanation',font_size=26),column='right')
        self.assertAlmostEqual(view.target('left').font_size,26*.85)
        self.assertAlmostEqual(view.target('left').font_size,view.target('right').font_size)
        self.assertAlmostEqual(view.target('diagram').get_left()[0],view.target('left').get_left()[0])
        self.assertEqual(view.layout_report()['overrides'],[])
        view.validate()

    def test_replanning_restores_natural_sizes_instead_of_repeatedly_shrinking(self):
        view=ColumnSlide()
        view.add('equation',MathRow({'call':'f(n)', 'rhs':'=f(n-1)+n'}))
        view.add('wide',self.wide(view))
        fitted=view.target('equation').font_size
        view.add('note',Text('The same size group',font_size=26))
        self.assertAlmostEqual(view.target('equation').font_size,fitted)
        expanded=view.fork().remove('wide')
        self.assertAlmostEqual(expanded.target('equation').font_size,33.6)
        self.assertAlmostEqual(view.target('equation').font_size,33.6*.85)
        self.assertEqual(expanded.target('equation').native_layout_findings(),[])

    def test_plain_prose_wraps_before_font_size_is_reduced(self):
        view=SplitSlide()
        source='Keep the definition on screen while we explain how each choice leads to a smaller problem.'
        view.add('explanation',source)
        target=view.target('explanation')
        self.assertIn('\n',target.original_text)
        self.assertEqual(target._algovis_source_text,source)
        self.assertAlmostEqual(target.font_size,26)
        self.assertLessEqual(target.width,view._text_width('left')+1e-7)

    def test_automatic_fitting_can_be_explicitly_disabled(self):
        view=ColumnSlide(auto_fit=False)
        with self.assertRaisesRegex(ValueError,'exceeds'):
            view.add('wide',self.wide(view))
        self.assertEqual(view.items,{})
        self.assertFalse(view.layout_report()['autoFit'])

    def test_readability_failure_rolls_back_the_whole_plan(self):
        view=ColumnSlide()
        view.add('note','Small text already',font_scale=16/26,
                 font_reason='Exercise the readability boundary')
        original=view.target('note').get_all_points().copy()
        with self.assertRaisesRegex(ValueError,'text too small'):
            view.add('wide',self.wide(view))
        self.assertEqual(list(view.items),['note'])
        np.testing.assert_allclose(view.target('note').get_all_points(),original)

    def test_retained_objects_recover_their_natural_size_in_a_roomier_layout(self):
        first=SplitSlide()
        handle=first.add('text',Text('Keep this definition',font_size=26))
        first.add('wide',self.wide(first,'left'))
        first.install(Scene())
        self.assertAlmostEqual(handle.mobject.font_size,26*.85)
        second=ColumnSlide()
        second.add('text',handle)
        self.assertAlmostEqual(second.target('text').font_size,26)
        self.assertAlmostEqual(handle.mobject.font_size,26*.85)

    def test_fitted_proof_equations_keep_native_baselines_and_label_alignment(self):
        view=ProofSlide()
        row=MathRow({'call':'f(k+1)', 'rhs':'=f(k)+(k+1)'})
        width=view._text_width('INDUCTIVE STEP')
        row.scale(width/row.width/.85)
        view.add('inductive_step',row)
        target=view.target('inductive_step')
        self.assertEqual(target.native_layout_findings(),[])
        self.assertAlmostEqual(view.target('label:inductive_step').get_top()[1],target.get_top()[1])
        self.assertAlmostEqual(target.get_left()[0],view.frame.left[0])
        self.assertAlmostEqual(target.font_size,33.6)
        self.assertAlmostEqual(view.items['inductive_step'].fit_scale,1.)

    def test_custom_policy_is_explicit_and_validated(self):
        with self.assertRaises(ValueError):FitPolicy(min_scale=0)
        with self.assertRaises(ValueError):FitPolicy(min_font_size=-1)
        view=ColumnSlide(auto_fit=FitPolicy(min_scale=.4))
        diagram=Rectangle(width=2,height=9)
        view.add('diagram',diagram)
        self.assertLess(view.target('diagram').height,diagram.height)
        self.assertAlmostEqual(view.target('diagram').width/view.target('diagram').height,2/9)

    def test_wrapped_proof_prose_aligns_the_label_to_its_first_line(self):
        from algovis.core.proof import first_line_of
        view=ProofSlide(profile='worked')
        view.add('claim','The function returns the optimal additional value obtainable from all items under consideration, with the current weight already in the bag.')
        text=view.target('claim')
        self.assertIn('\n',text.original_text)
        self.assertAlmostEqual(view.target('label:claim').get_top()[1],first_line_of(text).get_top()[1])

    def test_retained_prose_rewraps_for_its_new_column_without_changing_font_metrics(self):
        from algovis import ViewTransition
        from tests.test_composition import apply
        first=SplitSlide()
        handle=first.add('text','Keep the definition on screen while we explain how each choice leads to a smaller problem.')
        scene=Scene();first.install(scene)
        old_lines=handle.mobject.original_text.count('\n')
        second=ColumnSlide();second.add('text',handle)
        self.assertLess(second.target('text').original_text.count('\n'),old_lines)
        apply(ViewTransition(first,second),scene)
        self.assertEqual(handle.mobject.original_text,second.target('text').original_text)
        self.assertAlmostEqual(handle.mobject.font_size,26)


class RelativeFontTests(unittest.TestCase):
    def test_relative_font_sizes_preserve_the_requested_hierarchy(self):
        view=ColumnSlide()
        view.add('body','The main explanation')
        view.add('note','A supporting note',font_scale=.85,font_reason='Supporting explanation')
        view.add('emphasis','The important bit',font_scale=1.2,font_reason='Primary takeaway')
        self.assertAlmostEqual(view.target('body').font_size,26)
        self.assertAlmostEqual(view.target('note').font_size,26*.85)
        self.assertAlmostEqual(view.target('emphasis').font_size,26*1.2)
        self.assertEqual(view.layout_report()['fontScales'],{'note':.85,'emphasis':1.2})

    def test_relative_sizes_survive_a_shared_automatic_fit(self):
        view=ColumnSlide()
        view.add('body','The main explanation')
        view.add('note','A supporting note',font_scale=.85,font_reason='Supporting explanation')
        view.add('wide',Rectangle(width=view._text_width('body')/.85,height=.5))
        self.assertAlmostEqual(view.target('note').font_size/view.target('body').font_size,.85)

    def test_fork_can_change_font_scale_without_touching_the_live_object(self):
        first=ColumnSlide()
        handle=first.add('note','A supporting note',font_scale=.85,font_reason='Supporting explanation')
        first.install(Scene())
        second=first.fork().set_font_scale('note',1.1,reason='Promote the explanation')
        self.assertIs(second.object('note'),handle)
        self.assertAlmostEqual(handle.mobject.font_size,26*.85)
        self.assertAlmostEqual(second.target('note').font_size,26*1.1)
        self.assertAlmostEqual(first.target('note').font_size,26*.85)

    def test_named_math_adopts_relative_sizing_and_preserves_its_native_baseline(self):
        from algovis import ViewTransition
        from tests.test_composition import apply
        first=ColumnSlide()
        handle=first.add('call',MathRow({'f':'f(', 'i':'i', 'end':')'}),font_scale=1.2,font_reason='Primary example')
        scene=Scene();first.install(scene)
        second=first.fork().set_font_scale('call',.8,reason='Retain as a reference').substitute('call',i='i+1')
        apply(ViewTransition(first,second),scene)
        self.assertAlmostEqual(handle.mobject.font_size,33.6*.8)
        self.assertEqual(handle.mobject.native_layout_findings(),[])
        self.assertEqual(handle.mobject._algovis_relative_font_scale,.8)
        roomier=ColumnSlide();roomier.add('call',handle)
        self.assertAlmostEqual(roomier.target('call').font_size,33.6*.8)

    def test_invalid_or_unreadable_overrides_fail_without_altering_the_plan(self):
        view=ColumnSlide()
        for scale in (0,-1,float('nan')):
            with self.assertRaises(ValueError):view.add('bad','Text',font_scale=scale)
        with self.assertRaisesRegex(ValueError,'text too small'):
            view.add('tiny','Text',font_scale=.5,font_reason='Exercise the readability boundary')
        with self.assertRaises(TypeError):view.add('diagram',Rectangle(),font_scale=.8,font_reason='Invalid diagram override')
        self.assertEqual(view.items,{})

    def test_intentional_relative_sizes_are_not_reported_as_a_peer_font_error(self):
        from algovis.review.inspection import typography_findings
        snapshot={'objects':[
            {'id':'a','label':'main','fontSize':26,'typographyGroup':'body','typeRole':'body'},
            {'id':'b','label':'note','fontSize':22.1,'relativeFontScale':.85,
             'typographyGroup':'body','typeRole':'body'}]}
        self.assertEqual(typography_findings(snapshot),[])
        snapshot['objects'][1]['fontSize']=24
        self.assertEqual(len(typography_findings(snapshot)),1)


if __name__=='__main__':unittest.main()
