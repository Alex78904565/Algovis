import unittest
from algovis import CaseEquation,Equation,ProofSlide,SceneSequence,TextObject


class CaseColumnTests(unittest.TestCase):
    def test_case_lhs_baseline_stays_fixed_when_its_condition_grows(self):
        from algovis import DerivationScene
        view=DerivationScene()
        view.add('rule',CaseEquation(Equation({'call':'f(i)=\\max'}),[
            Equation({'choice':r'\text{take item }i'}),Equation({'choice':r'\text{skip item }i'})]),slot='equation')
        rows=view.target('rule').rows
        later=view.fork().refine('rule',rows=[rows[0].next_layout({**rows[0].slot_tex,'condition':r'\quad(\text{if it fits})'}),rows[1]])
        sequence=SceneSequence('Build a restriction');sequence.add(view,reason='List choices');sequence.add(later,reason='Restrict one choice')
        sequence.compile()
        a,b=[beat.scene for beat in sequence.beats]
        self.assertAlmostEqual(a.target('rule').lhs.baseline,b.target('rule').lhs.baseline)

    def test_case_annotations_share_a_column_through_typography_and_adoption(self):
        from algovis import RecurrenceScene
        equation=CaseEquation(Equation({'call':'f(i,w)=\\max'}),[
            Equation({'value':'v_i+f(i+1,w+w_i)','condition':r'\quad\text{if }w+w_i\le C','choice_label':r'\quad(\text{take }i)'}),
            Equation({'value':'f(i+1,w)','choice_label':r'\quad(\text{skip }i)'})],aligned_parts=('choice_label',))
        view=RecurrenceScene();view.add('recurrence',equation,slot='equation')
        planned=view.target('recurrence')
        self.assertAlmostEqual(planned.rows[0].part('choice_label').get_left()[0],planned.rows[1].part('choice_label').get_left()[0])
        for row in planned.rows:self.assertEqual(row.native_layout_findings(),[])
        changed=planned.with_state(rows=[row.next_layout() for row in planned.rows])
        equation.adopt_layout(changed)
        self.assertEqual(equation.aligned_parts,('choice_label',))
        self.assertAlmostEqual(equation.rows[0].part('choice_label').get_left()[0],equation.rows[1].part('choice_label').get_left()[0])

    def test_restate_claim_keeps_algorithm_and_retires_old_justification(self):
        view=ProofSlide()
        recurrence=Equation({'rule':'f(i)=f(i+1)'})
        base=Equation({'base':'f(n)=0'})
        view.define_algorithm(recurrence,base)
        view.add('claim',Equation({'predicate':'P(k):','meaning':r'\text{correct with k items}'}))
        for row in ('base_case','induction_hypothesis','inductive_step','work','conclusion'):
            view.add(row,TextObject('Justification for the original claim'))
        definitions=view.object('definitions').mobject
        changed=view.restate_claim({'predicate':'P(k):','meaning':r'\text{correct starting at k}'})
        self.assertIs(changed.object('definitions').mobject,definitions)
        self.assertEqual(set(changed.items),{'proof_rail','definitions','label:definitions','claim','label:claim'})
        self.assertIn('base_case',view.items)
