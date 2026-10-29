"""Object-owned word attention, with a silent eight-second timing fixture.

python -m manim -ql examples/word_attention.py WordAttentionExample

For a recorded lesson, replace the fixture with begin_narration(cue_json).
Each cue identifies the intended occurrence, not every use of a common word.
"""
from algovis import (ColumnSlide, LessonStyle, MathRow, NarrationCue,
                     NarrationTrack, ViewScene)


class WordAttentionExample(ViewScene):
    def construct(self):
        # Explicit fixture words make this example runnable without recordings.
        words = [('recurrence', 0.), ('input', 2.), ('smaller', 4.), ('add', 6.)]
        self.narration = NarrationTrack('unused.wav', 8.,
            [NarrationCue(word, time, word) for word, time in words],
            words=[{'word': word, 'start': time, 'end': time+.3}
                   for word, time in words])
        self.narration.start_time = self.renderer.time

        board = ColumnSlide('Reuse a smaller answer', theme=self.theme)
        call = board.add('recurrence', MathRow({
            'call': 'f(', 'input': 'n', 'equals': ')=',
            'child': 'f(n-1)', 'plus': '+', 'effect': 'n'}))
        call.part('input').on_word('input', duration=.6,
            reason='Identify the input inside the call')
        call.part('child').on_word('smaller', duration=.6,
            reason='Identify the already available smaller answer')
        call.part('plus').on_word('add', style='plus', duration=.6,
            reason='Show how the current contribution combines with that answer')
        board.add('note', LessonStyle(theme=self.theme).text(
            'The same expression stays on screen.', type_role='label'))
        self.transition_to(board, cue='recurrence', run_time=.6,
                           reason='Introduce the recurrence once')
        self.narration.finish(self)
