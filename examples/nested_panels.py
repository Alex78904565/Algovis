"""manim -ql examples/nested_panels.py NestedPanelsExample"""
from algovis import Equation,Panel,PanelSlide,RowPanel,TextObject,ViewScene


class NestedPanelsExample(ViewScene):
    def construct(self):
        film=self.lesson_animation()
        explanation=film.group('one definition and its application')

        columns=RowPanel(gap=1.)
        definition=columns.panel('definition',Panel())
        definition.add('heading',TextObject('Definition',type_role='heading'))
        definition.add('equation',Equation({'call':'f(k)','eq':'=',
                                          'value':r'\frac{k(k+1)}2'}))
        application=columns.panel('application',Panel())
        application.add('heading',TextObject('Application',type_role='heading'))

        first=PanelSlide().add_panel('working',columns)
        explanation.add(first,duration=.6,reason='Introduce the retained definition')

        second=first.fork()
        second.add_at('working/application/equation',first.copy('working/definition/equation'))
        explanation.add(second,duration=1.6,reason='Carry a copy into the application panel')

        third=second.fork().substitute('working/application/equation',call='f(2)',value=r'\frac{2(2+1)}2')
        explanation.add(third,duration=1.,reason='Substitute two without replacing the surrounding board')

        fourth=third.fork().substitute('working/application/equation',value='3')
        explanation.add(fourth,duration=1.,reason='Evaluate the copied definition in place')
        film.play(self)
        self.wait(1.)
