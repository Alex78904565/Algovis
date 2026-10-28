"""Small public examples of shared geometry, semantics and proof composition.

python -m manim -ql examples/extensible_components.py SharedCellsExample ProofExample
These examples have no narration. Narrated scenes use the corresponding *_on_cue
helpers shown in docs/COMPONENT_ARCHITECTURE.md.
"""
from manim import DOWN, FadeIn, LEFT, MathTex, RIGHT, Text, UP, VGroup
from algovis import (CallNode, LessonStyle, Proof, SemanticProperties,
                     SlideScene, StateRow)


class SharedCellsExample(SlideScene):
    def construct(self):
        row=StateRow(['','',''],theme=self.theme).move_to(DOWN)
        node=CallNode(MathTex('f(3)'),shape='square',theme=self.theme,
                      semantics=SemanticProperties(role='node')).move_to(UP)
        self.play(FadeIn(row),FadeIn(node))
        for cell,value in zip(row,[1,1,2]):
            self.play(cell.populate(value),run_time=.5)
        self.play(node.populate(2),run_time=.6)
        self.wait(1)


class ProofExample(SlideScene):
    def construct(self):
        style=LessonStyle(theme=self.theme)
        proof=Proof(theme=self.theme)
        proof.add_row('definitions',style.math('f(n)=f(n-1)+n'))
        proof.add_row('claim',VGroup(style.text('P(k): the function gives the sum',type_role='label'),
                                    style.text('of the first k positive integers',type_role='label'))
                      .arrange(DOWN,aligned_edge=LEFT,buff=.12))
        proof.add_row('base_case',style.math('f(0)=0',status='known'))
        proof.add_row('induction_hypothesis',style.text('Assume the smaller answer is correct',type_role='label'))
        proof.add_row('inductive_step',style.math('f(k+1)=f(k)+(k+1)'))
        self.play(FadeIn(proof))
        self.wait(1)
