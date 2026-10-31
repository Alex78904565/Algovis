"""manim -ql examples/panel_motion.py PanelMotionExample"""
from algovis import CaseEquation,Equation,Panel,PanelSlide,RowPanel,TextObject,ViewScene


class PanelMotionExample(ViewScene):
    def construct(self):
        film=self.lesson_animation()
        steps=film.group('move one complete mathematical object')
        columns=RowPanel(gap=1.)
        source=columns.panel('source',Panel())
        source.add('heading',TextObject('Source',type_role='heading'))
        source.add('rule',CaseEquation(
            Equation({'call':'f(k)','eq':'='},roles={'call':'current'}),[
                Equation({'value':'f(k-1)+k','condition':r'\quad k>0'}),
                Equation({'value':'0','condition':r'\quad k=0'})],aligned_parts=('condition',)))
        target=columns.panel('target',Panel())
        target.add('heading',TextObject('Destination',type_role='heading'))
        first=PanelSlide().add_panel('working',columns)
        steps.add(first,duration=.6,reason='Show the complete recurrence')
        second=first.fork().reparent('working/source/rule','working/target/rule')
        steps.add(second,duration=2.,reason='Move its brace, function and alternatives together')
        film.play(self)
        self.wait(.8)
