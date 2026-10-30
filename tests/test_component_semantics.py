import unittest
from unittest.mock import patch

import numpy as np
from manim import MathTex, Rectangle, Scene, Text, VGroup, UP, ManimColor

from algovis import (CallNode, DEFAULT_THEME, LessonStyle, MathRow, Proof,
                     ProofRow, RecursiveTree, SemanticChange, SemanticProperties,
                     SlideScene, StateCell, StateCellStyle, StateRow, set_semantics)


class SemanticPropertyTests(unittest.TestCase):
    def test_induction_status_tints_the_frame_without_changing_label_ink(self):
        from algovis import INDUCTION_STATE_CELL_STYLE
        from manim import interpolate_color
        cell=StateCell('P(0)',width=1.4,style=INDUCTION_STATE_CELL_STYLE)
        original_fill=cell.box.get_fill_color()
        change=SemanticChange(cell,status='known')
        self.assertEqual(cell.box.get_fill_color(),original_fill)
        change.begin();change.interpolate(.5)
        self.assertNotEqual(cell.box.get_fill_color(),original_fill)
        self.assertEqual(cell.label.get_color(),cell.theme.foreground)
        change.finish()
        self.assertEqual(cell.box.get_stroke_color(),cell.theme.success)
        self.assertEqual(cell.box.get_fill_color(),interpolate_color(ManimColor(cell.theme.background),ManimColor(cell.theme.success),.3))
        self.assertAlmostEqual(cell.box.get_fill_opacity(),INDUCTION_STATE_CELL_STYLE.fill_opacity)
        self.assertEqual(cell.label.get_color(),cell.theme.foreground)

    def test_tinted_frame_still_obeys_evaluation_precedence(self):
        from algovis import INDUCTION_STATE_CELL_STYLE
        from manim import interpolate_color
        cell=StateCell('5',style=INDUCTION_STATE_CELL_STYLE,status='computed',evaluation='bad')
        self.assertEqual(cell.box.get_stroke_color(),cell.theme.danger)
        self.assertEqual(cell.box.get_fill_color(),interpolate_color(ManimColor(cell.theme.background),ManimColor(cell.theme.danger),.3))
        self.assertEqual(cell.label.get_color(),cell.theme.foreground)

    def test_ordinary_cell_semantics_preserve_existing_nonstatus_fill(self):
        cell=StateCell('5')
        cell.box.set_fill(DEFAULT_THEME.primary,opacity=.2)
        set_semantics(cell,status='computed')
        self.assertEqual(cell.box.get_fill_color(),DEFAULT_THEME.primary)
        self.assertAlmostEqual(cell.box.get_fill_opacity(),.2)

    def test_scale_attention_preserves_live_semantic_paint_at_intermediate_frames(self):
        from algovis import Pulse
        cell = StateCell('5')
        status, pulse = SemanticChange(cell, status='computed'), Pulse(cell)
        status.begin(); pulse.begin()
        status.interpolate(.5)
        expected = cell.box.get_stroke_color()
        pulse.interpolate(.5)
        self.assertEqual(cell.box.get_stroke_color(), expected)
        status.finish(); pulse.finish()
        self.assertEqual(cell.box.get_stroke_color(), cell.theme.success)

    def test_evaluation_overrides_status_without_discarding_the_status(self):
        obj=set_semantics(MathTex('O(2^n)'),status='computed',evaluation='bad')
        self.assertEqual(obj.get_color(),DEFAULT_THEME.danger)
        self.assertEqual(obj.semantics.status,'computed')
        self.assertEqual(obj._algovis_semantics['evaluation'],'bad')
        set_semantics(obj,role='current')
        self.assertEqual(obj.get_color(),DEFAULT_THEME.danger)
        set_semantics(obj,evaluation=None)
        self.assertEqual(obj.get_color(),DEFAULT_THEME.success)

    def test_change_construction_does_not_paint_live_content_before_its_cue(self):
        obj=set_semantics(MathTex('5'),status='computed')
        anim=SemanticChange(obj,evaluation='bad')
        self.assertEqual(obj.get_color(),DEFAULT_THEME.success)
        self.assertIsNone(obj.semantics.evaluation)
        anim.begin();anim.interpolate(.5);anim.finish()
        self.assertEqual(obj.get_color(),DEFAULT_THEME.danger)
        self.assertEqual(obj.semantics.evaluation,'bad')

    def test_cells_apply_properties_to_the_frame_without_recoloring_the_value(self):
        obj=StateCell('5',color=DEFAULT_THEME.success,
                      semantics=SemanticProperties(status='computed',evaluation='bad'))
        self.assertEqual(obj.box.get_stroke_color(),DEFAULT_THEME.danger)
        self.assertEqual(obj.label.get_color(),DEFAULT_THEME.foreground)

    def test_native_substitution_preserves_the_declared_meaning(self):
        row=MathRow({'f':'f(','i':'i','close':')'})
        set_semantics(row.part('i'),status='known',evaluation='bad')
        target=row.next_layout(i='1');scene=Scene();scene.add(row);row.commit(target,scene)
        self.assertEqual(row.part('i').semantics.evaluation,'bad')
        self.assertEqual(row.part('i').get_color(),DEFAULT_THEME.danger)
        self.assertEqual(row.native_layout_findings(),[])

    def test_authoring_factories_store_properties_as_well_as_paint(self):
        obj=LessonStyle().math('O(2^n)',role='current',status='computed',evaluation='bad')
        self.assertEqual(obj.semantics,SemanticProperties('current','computed','bad'))
        self.assertEqual(obj.get_color(),DEFAULT_THEME.danger)
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            SemanticProperties(status='rejected',evaluation='good').color()


class SharedConstructionTests(unittest.TestCase):
    def test_population_keeps_the_opted_in_status_tint_and_white_value(self):
        from algovis import INDUCTION_STATE_CELL_STYLE
        from manim import interpolate_color
        cell=StateCell('',style=INDUCTION_STATE_CELL_STYLE)
        animation=cell.populate(1);scene=Scene();scene.add(cell)
        animation._setup_scene(scene);animation.begin();animation.finish();animation.clean_up_from_scene(scene)
        self.assertEqual(cell.box.get_fill_color(),interpolate_color(ManimColor(cell.theme.background),ManimColor(cell.theme.success),.3))
        self.assertEqual(cell.label.get_color(),cell.theme.foreground)
        self.assertEqual(cell.label.tex_string,'1')

    def test_merging_a_named_call_into_its_value_adopts_the_new_glyph_calibration(self):
        from algovis.layout import measured_font_size
        source=StateCell('f(3)');target=StateCell('2')
        source.apply_scene_typography(LessonStyle().typography,group='cells')
        target.apply_scene_typography(LessonStyle().typography,group='cells')
        source_label=source.label
        motion=source.motions_to(target)[0];motion.begin();motion.finish()
        self.assertIs(source.label,source_label)
        self.assertAlmostEqual(measured_font_size(source.label),measured_font_size(target.label))
        self.assertEqual(source.label.tex_string,'2')

    def test_a_new_cell_value_stays_centred_throughout_its_reveal(self):
        cell=StateCell('').shift(UP*2)
        label=cell.label
        animation=cell.populate(1)
        scene=Scene();scene.add(cell);animation._setup_scene(scene);animation.begin()
        for progress in (.1,.3,.6,.9):
            animation.interpolate(progress)
            np.testing.assert_allclose(animation.entering_label.get_center(),cell.box.get_center())
        animation.finish();animation.clean_up_from_scene(scene)
        self.assertIs(cell.label,label)
        self.assertEqual(cell.label.tex_string,'1')
        np.testing.assert_allclose(cell.label.get_center(),cell.box.get_center())
    def test_population_waits_until_playback_and_keeps_value_and_frame_in_one_cell(self):
        cell=StateCell('')
        animation=cell.populate(1)
        self.assertEqual(cell.label.tex_string,'')
        self.assertIsNone(cell.semantics.status)
        animation.begin();animation.interpolate(.5);animation.finish()
        self.assertEqual(cell.label.tex_string,'1')
        self.assertAlmostEqual(cell.label.font_size,StateCell('1').label.font_size)
        self.assertEqual(cell.semantics.status,'computed')
        self.assertEqual(cell.box.get_stroke_color(),DEFAULT_THEME.success)
        self.assertIs(cell.box,cell[0]);self.assertIs(cell.label,cell[1])
        self.assertEqual(len(cell),2)

    def test_population_inherits_parent_scale_and_preserves_explicit_bad_evaluation(self):
        reference=StateCell('8')
        cell=StateCell('',evaluation='bad').scale(.6)
        animation=cell.populate(8)
        animation.begin();animation.finish()
        self.assertAlmostEqual(cell.label.height,reference.label.height*.6,places=5)
        self.assertAlmostEqual(cell.label.font_size,reference.label.font_size*.6)
        self.assertEqual(cell.box.get_stroke_color(),DEFAULT_THEME.danger)
        animation=cell.populate(3)
        animation.begin();animation.finish()
        self.assertEqual(cell.label.tex_string,'3')
        self.assertAlmostEqual(cell.label.get_x(),cell.box.get_x())
        with self.assertRaisesRegex(ValueError,'wider cell'):
            cell.populate('12345678901234567890')

    def test_tree_and_array_share_the_cell_implementation_and_frame_style(self):
        from algovis.core import structures
        style=StateCellStyle(stroke_width=3.7,fill_opacity=.6,corner_radius=.04)
        with patch.object(structures,'DEFAULT_STATE_CELL_STYLE',style):
            row=StateRow([1,2])
            tree=RecursiveTree(lambda n:(f'f({n})',[]),(2,),node_shape='square')
        node=tree.tree_structure['mobject']
        self.assertIsInstance(node,CallNode);self.assertIsInstance(node,StateCell)
        self.assertIs(node[0],node.box);self.assertIs(node[1],node.label)
        for cell in (node,*row):
            self.assertEqual(cell.frame_style,style)
            self.assertAlmostEqual(cell.box.get_stroke_width(),3.7)
        self.assertLess(node.label.width,node.box.width)

    def test_cell_and_node_subclasses_are_explicit_extension_points(self):
        class MarkedCell(StateCell):pass
        class MarkedCall(CallNode):pass
        row=StateRow([1],cell_type=MarkedCell)
        tree=RecursiveTree(lambda n:('f(n)',[]),(1,),node_type=MarkedCall)
        self.assertIsInstance(row[0],MarkedCell)
        self.assertIsInstance(tree.tree_structure['mobject'],MarkedCall)

    def test_custom_node_artwork_changes_only_its_frame_status(self):
        from algovis import NodeState
        tree=RecursiveTree(lambda n:('f(n)',[]),(1,),
            node_factory=lambda text,label:Rectangle(width=1.2,height=.8))
        data=tree.tree_structure;original_ink=data['label'].get_color()
        animation=tree.get_set_state_anim(data,NodeState.RESOLVED)
        animation.begin();animation.finish()
        self.assertEqual(data['label'].get_color(),original_ink)
        self.assertEqual(data['mobject'].box.get_stroke_color(),DEFAULT_THEME.success)

    def test_proof_row_label_follows_the_first_line_and_copies_follow_their_copy(self):
        body=VGroup(Text('Assume P(k)'),Text('every smaller answer works')).arrange(UP)
        row=ProofRow(Text('HYPOTHESIS'),body,first_line=body[0])
        row.label.update(0)
        self.assertAlmostEqual(row.label.get_top()[1],body[0].get_top()[1])
        copy=row.copy();copy.content.shift(UP);copy.label.update(0)
        self.assertAlmostEqual(copy.label.get_top()[1],copy.content[0].get_top()[1])
        self.assertNotAlmostEqual(copy.label.get_top()[1],row.label.get_top()[1])

    def test_proof_rows_use_the_transformed_parent_frame(self):
        proof=Proof()
        original_center=proof.get_center().copy()
        expected=original_center+.7*(proof.frame.anchor('claim')-original_center)+UP
        proof.scale(.7).shift(UP)
        obj=Text('The claim',font_size=20);old_height=obj.height
        row=proof.add_row('claim',obj)
        self.assertAlmostEqual(row.content.height,old_height*.7)
        self.assertAlmostEqual(row.content.get_left()[0],expected[0])
        np.testing.assert_allclose(proof.anchor('claim'),expected)
        self.assertAlmostEqual(row.label.get_top()[1],row.content.get_top()[1])

    def test_progressive_rows_wait_for_the_word_and_finish_with_one_owner(self):
        scene=SlideScene();proof=Proof();scene.add(proof)
        calls=[]
        scene.wait_for_word=lambda name:calls.append(('wait',len(proof.rows_by_name)))
        scene.play_on_cue=lambda name,*args,**kwargs:calls.append(('play',name))
        row=scene.proof_row_on_cue('claim_word',proof,'claim',Text('A claim'),reason='Name the claim')
        self.assertEqual(calls[0],('wait',0))
        self.assertIn(row.content,scene.get_mobject_family_members())
        self.assertEqual(scene.mobjects,[proof])
        scene.proof_row_on_cue('refine',proof,'claim',Text('A refined claim'),reason='Refine the claim')
        self.assertEqual(len(proof.rows),1)
        self.assertEqual(scene.mobjects,[proof])

    def test_definition_scene_helper_keeps_the_shared_transfer_operation(self):
        from algovis import ApplyDefinition
        scene=object.__new__(SlideScene);captured=[]
        scene.play_on_cue=lambda name,*args,**kw:captured.append((name,args,kw))
        source=Rectangle();application=Rectangle();result=Rectangle()
        self.assertIs(scene.apply_definition_on_cue('substitute',source,application,result,
                      reason='Use the definition'),result)
        self.assertIsInstance(captured[0][1][0],ApplyDefinition)
        self.assertIs(captured[0][1][0].definition,source)
        self.assertIs(captured[0][1][0].application,application)

    def test_whole_proof_row_definition_application_adopts_one_result(self):
        scene=SlideScene();scene.setup();scene.renderer.skip_animations=True
        self.addCleanup(scene.tear_down)
        proof=Proof();source=MathTex('f(0)=0').shift(UP*3)
        original=proof.add_row('base_case',MathTex('f(0)'))
        scene.add(proof,source)
        scene.play_on_cue=lambda name,*animations,**kw: scene.play(*animations,run_time=.1)
        result=MathTex('0')
        scene.apply_definition_on_cue('use_base',source,original.content,result,
            proof=proof,row='base_case',reason='Apply the base definition')
        self.assertIs(proof.row('base_case').content,result)
        self.assertIn(source,scene.mobjects)
        self.assertEqual(sum(obj is result for obj in scene.get_mobject_family_members()),1)
        self.assertNotIn(result,scene.mobjects)
        self.assertAlmostEqual(original.label.get_top()[1],result.get_top()[1])


if __name__=='__main__':unittest.main()
