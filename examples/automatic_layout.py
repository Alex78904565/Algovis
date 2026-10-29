"""Default wrapping, consistent fitting and reflow, without coordinates.

python -m manim -ql examples/automatic_layout.py AutomaticLayout
"""
from algovis import MathRow, SplitSlide, StateRow, ViewScene


class AutomaticLayout(ViewScene):
    def construct(self):
        board=SplitSlide('Readable layouts by default',theme=self.theme)
        board.add('explanation',
            'Keep the definition on screen while each choice leads to a smaller problem. '
            'The layout wraps ordinary prose and keeps the left edges aligned.')
        board.add('note','A smaller supporting note uses the same layout.',font_scale=.85)
        board.add('recurrence',MathRow({'call':'f(n)', 'rhs':'=f(n-1)+n'}),column='right')
        board.add('states',StateRow(['1','2','3','4'],width=1.4,theme=self.theme),column='right')
        self.transition_to(board,run_time=.8)
        self.wait(1.5)

        roomier=board.fork().remove('states')
        self.transition_to(roomier,run_time=1)
        self.wait(1.5)
