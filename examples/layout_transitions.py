"""Shared slide states: keep, move, copy, and substitute.

python -m manim -ql examples/layout_transitions.py LayoutTransitions ProofTransitions EquationTransitions
For narration, pass cue= and reason= to transition_to; the recording owns time.
"""
from algovis import (ColumnSlide, EquationSlide, LessonStyle, MathRow, ProofSlide,
                     SlideScene, SplitSlide)


class LayoutTransitions(SlideScene):
    def construct(self):
        style = LessonStyle(theme=self.theme)
        first = ColumnSlide('Using a definition', theme=self.theme)
        definition = first.add('definition', MathRow({
            'call': 'f(k)', 'equals': '=', 'value': r'\frac{k(k+1)}2'}))
        first.add('note', style.text('Keep the definition while we use a copy.', type_role='label'))
        self.transition_to(first, run_time=.6)
        self.wait(1)

        second = SplitSlide(first.object('title'), theme=self.theme)
        second.add('definition', definition)
        second.add('application', definition.copy(), column='right')
        second.substitute('application', call='f(3)', value=r'\frac{3(3+1)}2')
        self.transition_to(second, run_time=2)
        self.wait(1)

        third = second.fork().substitute('application', value='6')
        self.transition_to(third, run_time=1)
        self.wait(1.5)


class ProofTransitions(SlideScene):
    def construct(self):
        style = LessonStyle(theme=self.theme)
        proof = ProofSlide('Induction', theme=self.theme)
        proof.add('definitions', style.math(r'f(n)=f(n-1)+n'))
        proof.add('claim', style.text('The function adds the first n positive integers.', type_role='label'))
        proof.add('base_case', style.math('f(0)=0', status='known'))
        hypothesis = proof.add('induction_hypothesis', MathRow({
            'call': 'f(k)', 'equals': '=', 'value': r'\frac{k(k+1)}2'}))
        proof.add('inductive_step', MathRow({
            'call': 'f(k+1)', 'equals': '=', 'child': 'f(k)', 'rest': '+(k+1)'}))
        self.transition_to(proof, run_time=.7)
        self.wait(1)

        applied = proof.fork().substitute('inductive_step', child=r'\frac{k(k+1)}2',
                                         from_definition=hypothesis.part('value'))
        self.transition_to(applied, run_time=2)
        self.wait(1.5)


class LayoutStill(SlideScene):
    """Inspect a final layout without first rendering its animations."""
    def construct(self):
        view = SplitSlide('Two related expressions', theme=self.theme)
        view.add('definition', MathRow({'formula': r'f(k)=\frac{k(k+1)}2'}))
        view.add('application', MathRow({'formula': 'f(3)=6'}), column='right')
        self.set_view(view)
        self.wait(1)


class EquationTransitions(SlideScene):
    def construct(self):
        style = LessonStyle(theme=self.theme)
        definition = EquationSlide('From recursion to stored answers', theme=self.theme)
        definition.add('meaning', style.text('Fill n = 0, 1, 2, ... in that order.', type_role='label'))
        definition.add('recurrence', MathRow({'call': 'f(n)', 'equals': '=', 'child': 'f(n-1)', 'rest': '+n'}))
        definition.add('base', MathRow({'call': 'f(0)', 'equals': '=', 'value': '0'}))
        self.transition_to(definition, run_time=.6)
        self.wait(1)
        array = definition.fork().substitute('recurrence', call='f[n]', child='f[n-1]')
        array.substitute('base', call='f[0]')
        self.transition_to(array, run_time=1)
        self.wait(1.5)
