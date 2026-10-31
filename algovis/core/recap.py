"""Stable numbered recaps with a semantic brace for a shared subset."""
from manim import VGroup,Brace,LEFT,RIGHT,DOWN
from ..layout import LessonStyle,assign_scene_typography
from ..theme import DEFAULT_THEME


class Checklist(VGroup):
    _algovis_content_fields=('visible','brace_rows','recursion_brace','dp_brace')
    def __init__(self,steps,*,theme=DEFAULT_THEME,visible=0,brace_rows=4):
        self.theme,self.visible,self.brace_rows=theme,visible,brace_rows
        self.recursion_brace=False
        self.dp_brace=False
        style=LessonStyle(theme=theme)
        self.rows=VGroup(*(style.text(f'{index}.  {step}',type_role='body') for index,step in enumerate(steps,1)))
        self.rows.arrange(DOWN,aligned_edge=LEFT,buff=.35)
        self.brace=Brace(VGroup(*self.rows[:brace_rows]),RIGHT,color=theme.foreground)
        self.brace_label=style.text('just recursion',type_role='label').next_to(self.brace,RIGHT,buff=.2)
        self.storage_brace=(Brace(VGroup(*self.rows[brace_rows:]),RIGHT,color=theme.success)
                            if len(self.rows)>brace_rows else VGroup())
        self.storage_label=(style.text('the DP part',type_role='label').next_to(self.storage_brace,RIGHT,buff=.2)
                            if len(self.rows)>brace_rows else VGroup())
        super().__init__(self.rows,self.brace,self.brace_label,self.storage_brace,self.storage_label)
        for index,row in enumerate(self.rows):row.set_opacity(1 if index<visible else 0)
        self.brace.set_opacity(0);self.brace_label.set_opacity(0)
        self.storage_brace.set_opacity(0);self.storage_label.set_opacity(0)

    def apply_scene_typography(self,typography,*,group):
        center=self.get_center()
        for row in self.rows:assign_scene_typography(row,typography,group=group)
        assign_scene_typography(self.brace_label,typography,group=group,role='label')
        if len(self.rows)>self.brace_rows:
            assign_scene_typography(self.storage_label,typography,group=group,role='label')
        self.rows.arrange(DOWN,aligned_edge=LEFT,buff=.35)
        opacity=self.brace.get_stroke_opacity()
        shown=self.brace_label.get_fill_opacity()>.5
        self.brace.become(Brace(VGroup(*self.rows[:self.brace_rows]),RIGHT,color=self.theme.foreground))
        self.brace.set_opacity(1 if shown else 0)
        self.brace_label.next_to(self.brace,RIGHT,buff=.2)
        if len(self.rows)>self.brace_rows:
            self.storage_brace.become(Brace(VGroup(*self.rows[self.brace_rows:]),RIGHT,color=self.theme.success))
            self.storage_brace.set_opacity(1 if self.dp_brace else 0)
            self.storage_label.next_to(self.storage_brace,RIGHT,buff=.2).set_opacity(1 if self.dp_brace else 0)
        self.move_to(center)

    def with_state(self,*,visible=None,recursion_brace=None,dp_brace=None):
        target=self.copy()
        if visible is not None:
            target.visible=visible
            for index,row in enumerate(target.rows):row.set_opacity(1 if index<visible else 0)
        if recursion_brace is not None:
            target.recursion_brace=bool(recursion_brace)
            target.brace.set_opacity(1 if recursion_brace else 0)
            target.brace_label.set_opacity(1 if recursion_brace else 0)
        if dp_brace is not None:
            if dp_brace and len(self.rows)<=self.brace_rows:
                raise ValueError('The storage brace needs a step beyond the recursion group')
            target.dp_brace=bool(dp_brace)
            target.storage_brace.set_opacity(1 if dp_brace else 0)
            target.storage_label.set_opacity(1 if dp_brace else 0)
            if dp_brace:
                from ..semantics import set_semantics
                for row in target.rows[target.brace_rows:]:
                    set_semantics(row,status='stored',theme=self.theme)
        return target

    def adopt_layout(self,target):
        from ..composition import _adopt
        for row,planned in zip(self.rows,target.rows):_adopt(row,planned)
        self.brace.become(target.brace);_adopt(self.brace_label,target.brace_label)
        self.storage_brace.become(target.storage_brace);_adopt(self.storage_label,target.storage_label)
        self.visible,self.brace_rows,self.recursion_brace=target.visible,target.brace_rows,target.recursion_brace
        self.dp_brace=target.dp_brace
        self.submobjects=[self.rows,self.brace,self.brace_label,self.storage_brace,self.storage_label]
        return self

    def motions_to(self,target,*,skip=()):
        from manim import Transform
        return [*(Transform(row,planned) for row,planned in zip(self.rows,target.rows)),
                Transform(self.brace,target.brace),Transform(self.brace_label,target.brace_label),
                Transform(self.storage_brace,target.storage_brace),Transform(self.storage_label,target.storage_label)]
