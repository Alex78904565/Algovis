from manim import *

from ..theme import DEFAULT_SPACING, DEFAULT_THEME
from ..frames import PanelFrame


class PseudocodePanel(VGroup):
    """A lightweight code panel with synchronized line highlighting."""
    _algovis_content_fields=('visible_lines',)

    def __init__(self, lines, title="Pseudocode", font="Consolas",
                 font_size=24, width=None, line_buff=None,
                 theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        self.visible_lines=tuple(range(len(lines)))
        line_buff = DEFAULT_SPACING.tight + 0.04 if line_buff is None else line_buff
        self.lines = VGroup(*[
            Text(
                line, font=font, font_size=font_size,
                color=theme.foreground, disable_ligatures=True,
            )
            for line in lines
        ]).arrange(DOWN, aligned_edge=LEFT, buff=line_buff)
        panel_width = width or self.lines.width + 0.65
        self.background = PanelFrame(panel_width, self.lines.height + 0.82, theme=theme, role="muted")
        self.lines.move_to(self.background).align_to(self.background, LEFT)
        self.lines.shift(RIGHT * 0.3 + DOWN * 0.12)
        self.title = Text(title, font_size=18, color=theme.primary)
        self.title.next_to(
            self.background.get_top(), DOWN, buff=DEFAULT_SPACING.tight,
        )
        self.cursor = SurroundingRectangle(self.lines[0], color=theme.accent,
                                           buff=0.07, stroke_width=2)
        self.cursor.set_fill(theme.accent, opacity=0.08).set_opacity(0)
        self.current_line = None
        self._cursor_visible = False
        self.add(self.background, self.title, self.lines, self.cursor)

    def highlight_line(self, index, color=None):
        color = color or self.theme.accent
        target = SurroundingRectangle(self.lines[index], color=color,
                                      buff=0.07, stroke_width=2)
        target.set_fill(color, opacity=0.08)
        self.current_line = index
        if not self._cursor_visible:
            self.cursor.become(target).set_opacity(0)
            self._cursor_visible = True
            return FadeIn(self.cursor)
        return Transform(self.cursor, target)

    def clear_highlight(self):
        self.current_line = None
        self._cursor_visible = False
        return FadeOut(self.cursor)

    def step(self, index, *animations):
        return AnimationGroup(self.highlight_line(index), *animations)

    def apply_scene_typography(self,typography,*,group):
        from ..layout import assign_scene_typography
        center=self.get_center()
        for line in self.lines:assign_scene_typography(line,typography,group=group,role='label')
        assign_scene_typography(self.title,typography,group=group,role='label')
        self.lines.arrange(DOWN,aligned_edge=LEFT,buff=.22)
        self.background.stretch_to_fit_width(self.lines.width+.65).stretch_to_fit_height(self.lines.height+.9)
        self.lines.move_to(self.background).shift(DOWN*.15)
        self.title.next_to(self.background.get_top(),DOWN,buff=.18)
        self.move_to(center)

    def with_state(self,*,visible_lines):
        target=self.copy()
        target.visible_lines=tuple(visible_lines)
        for index,line in enumerate(target.lines):line.set_opacity(1 if index in visible_lines else 0)
        return target

    def adopt_layout(self,target):
        from ..composition import _adopt
        for line,planned in zip(self.lines,target.lines):_adopt(line,planned)
        for live,planned in ((self.background,target.background),(self.title,target.title),(self.cursor,target.cursor)):
            _adopt(live,planned)
        self.visible_lines=target.visible_lines
        self.submobjects=[self.background,self.title,self.lines,self.cursor]
        return self

    def motions_to(self,target,*,skip=()):
        # One owner keeps the opaque panel behind its text during movement.
        # Animating the background after separate line roots paints over them.
        return [Transform(self,target)]
