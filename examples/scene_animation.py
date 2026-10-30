"""Objects -> named scene locations -> a narration-independent animation."""
from algovis import (LessonAnimation, ListScene, MathRow,
                     ProofSlide, ViewScene)


class SceneAnimationExample(ViewScene):
    def construct(self):
        film=LessonAnimation()
        calculation=film.group('The state-times-work calculation')
        first=ListScene('Counting work')
        work=first.add('work',MathRow({
            'open':'(', 'count':'n', 'units':r'\text{ states})',
            'times':r'\times', 'per_state':r'(1\text{ addition per state})'}))
        calculation.add(first,reason='Establish the general state-times-work calculation')
        second=first.fork()
        example=second.add('example',work.copy())
        calculation.add(second,duration=1.3,reason='Carry a copy into the next calculation row')
        third=second.fork().substitute('example',count='191')
        calculation.add(third,reason='Change only the numerical input; keep units and type size')
        film.play(self)
        self.wait(.5)

        proof=ProofSlide('Applying the induction hypothesis')
        proof_steps=film.group('The complete induction proof')
        hypothesis=proof.add('induction_hypothesis',MathRow({
            'assume':r'\text{Assume }', 'call':'f(k)', 'eq':'=', 'value':r'\frac{k(k+1)}2'}))
        proof.add('inductive_step',MathRow({
            'call':'f(k+1)', 'eq':'=', 'child':'f(k)', 'rest':'+(k+1)'}))
        proof_steps.add(proof,reason='The proof sequence reserves all later algebra before playback')
        applied=proof.fork().substitute('inductive_step',child=r'\frac{k(k+1)}2',
                                        from_definition=hypothesis.part('value'))
        proof_steps.add(applied,duration=1.2,reason='Carry the definition to its application')
        film.play(self)
        self.wait(.8)
