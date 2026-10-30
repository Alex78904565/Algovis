"""Shared state cells and their two-input addition process."""
import math
from manim import (AnimationGroup,Arrow,Create,DOWN,FadeIn,FadeOut,LEFT,MathTex,
                   MoveAlongPath,ParametricFunction,RIGHT,Succession,SurroundingRectangle,
                   SVGMobject,Transform,UP,VGroup,config,linear)
from .structures import StateRow
from ..layout import LessonStyle
from ..theme import DEFAULT_THEME
from ..semantics import set_semantics


class StateSequence(VGroup):
    def __init__(self,values,*,indices=False,index_notation='array',known=False,theme=DEFAULT_THEME):
        if index_notation not in ('array','function'):raise ValueError('Choose function or array index notation')
        values=tuple(values)
        self.theme=theme
        prepared=[LessonStyle(theme=theme).math(str(value)) for value in values]
        cell_width=max(1.06,max((label.width for label in prepared),default=0)+.22)
        self.row=StateRow(prepared,width=cell_width,theme=theme)
        if known:
            for value,cell in zip(values,self.row):
                if str(value).strip():set_semantics(cell,status='computed',theme=theme)
        self.index_labels=VGroup()
        self._pair=self._plus=self._arrow=None
        self._continuation=False
        if indices:
            for index,cell in enumerate(self.row,1):
                self.index_labels.add(LessonStyle(theme=theme).math(
                    (rf'f[{index}]' if index_notation=='array' else rf'f({index})'),
                    type_role='label',role='current').next_to(cell,DOWN,buff=.12))
        self.ellipsis=MathTex(r'\cdots',color=theme.muted)
        self.ellipsis.next_to(self.row,RIGHT,buff=.55).set_opacity(0)
        super().__init__(self.row,self.index_labels)

    def apply_scene_typography(self,typography,*,group):
        self.row.apply_scene_typography(typography,group=group)
        for label,cell in zip(self.index_labels,self.row):
            label.scale(typography.label/label.font_size).next_to(cell,DOWN,buff=.12)
            LessonStyle._watch_type(label,group+'/indices','label')
        self.ellipsis.scale(typography.label/self.ellipsis.font_size)
        LessonStyle._watch_type(self.ellipsis,group+'/indices','label')
        self.ellipsis.next_to(self.row,RIGHT,buff=.55)

    def cell(self,index):return self.row[index]

    def with_state(self,*,continuation):
        target=self.copy();target._continuation=bool(continuation)
        if continuation:
            target.ellipsis.next_to(target.row,RIGHT,buff=.55).set_opacity(1)
            if target.ellipsis not in target.submobjects:target.add(target.ellipsis)
        elif target.ellipsis in target.submobjects:target.remove(target.ellipsis)
        return target

    def motions_to(self,target):
        motions=[Transform(self.row,target.row),Transform(self.index_labels,target.index_labels)]
        if target._continuation and not self._continuation:
            self.ellipsis.become(target.ellipsis);self.add(self.ellipsis)
            motions.append(FadeIn(self.ellipsis))
        elif self._continuation and not target._continuation:motions.append(FadeOut(self.ellipsis))
        elif self._continuation:motions.append(Transform(self.ellipsis,target.ellipsis))
        return motions

    def adopt_layout(self,target):
        from ..composition import _adopt
        _adopt(self.row,target.row);_adopt(self.index_labels,target.index_labels)
        _adopt(self.ellipsis,target.ellipsis)
        self._continuation=target._continuation
        self.submobjects=[self.row,self.index_labels]+([self.ellipsis] if self._continuation else [])
        return self

    def populate(self,index,value):return self.row[index].populate(value)

    def begin_addition(self,left=0):
        self._pair=SurroundingRectangle(VGroup(self.row[left],self.row[left+1]),
                                        color=self.theme.accent,buff=.08)
        self._plus=LessonStyle(theme=self.theme).math('+',type_role='label',role='operation')
        self._plus.move_to((self.row[left].get_right()+self.row[left+1].get_left())/2)
        return AnimationGroup(Create(self._pair),FadeIn(self._plus),lag_ratio=0)

    def add_next(self,index,value):
        if self._pair is None:raise ValueError('Introduce the two-input addition before computing the next cell')
        pair=SurroundingRectangle(VGroup(self.row[index-2],self.row[index-1]),color=self.theme.accent,buff=.08)
        plus=self._plus.copy().move_to((self.row[index-2].get_right()+self.row[index-1].get_left())/2)
        arrow=Arrow(pair.get_right()+RIGHT*.025,self.row[index].box.get_left()+LEFT*.025,
                    buff=0,color=self.theme.primary,stroke_width=2.4,tip_length=.09)
        motions=[Transform(self._pair,pair),Transform(self._plus,plus),self.populate(index,value)]
        if self._arrow is None:self._arrow=arrow;motions.append(Create(arrow))
        else:motions.append(Transform(self._arrow,arrow))
        return AnimationGroup(*motions,lag_ratio=0)

    def continue_addition(self):
        pair=SurroundingRectangle(VGroup(self.row[-2],self.row[-1]),color=self.theme.accent,buff=.08)
        plus=self._plus.copy().move_to((self.row[-2].get_right()+self.row[-1].get_left())/2)
        self.ellipsis.next_to(self.row,RIGHT,buff=.55).set_opacity(1)
        if self.ellipsis not in self.submobjects:self.add(self.ellipsis)
        self._continuation=True
        arrow=Arrow(pair.get_right()+RIGHT*.025,self.ellipsis.get_left()+LEFT*.12,
                    buff=0,color=self.theme.primary,stroke_width=2.4,tip_length=.09)
        return AnimationGroup(Transform(self._pair,pair),Transform(self._plus,plus),
                              Transform(self._arrow,arrow),FadeIn(self.ellipsis),lag_ratio=0)

    def clear_addition(self):
        guides=[mob for mob in (self._pair,self._plus,self._arrow) if mob is not None]
        self._pair=self._plus=self._arrow=None
        return AnimationGroup(*(FadeOut(mob) for mob in guides))

    def fill_in_order(self,values):
        """Base entries first, followed by the shared two-input addition lane."""
        from ..utils.effects import DeferredAnimation
        steps=[]
        for index,value in enumerate(values):
            if index==2:steps.append(DeferredAnimation(self.begin_addition,run_time=.25))
            steps.append(DeferredAnimation(lambda index=index,value=value:
                self.populate(index,value) if index<2 else self.add_next(index,value),run_time=.48))
        steps.append(DeferredAnimation(self.clear_addition,run_time=.15))
        return Succession(*steps)

    def cross_out(self):
        from manim import Cross
        return Create(Cross(self,stroke_color=self.theme.danger,stroke_width=4))


class FloatingCharacter(SVGMobject):
    """A small character crosses the frame on a smooth sinusoidal path."""
    def __init__(self,path):
        super().__init__(path)

    def fly_across(self,*,under=None):
        self.scale_to_fit_height(.88).set_opacity(.78).set_z_index(2)
        baseline=under.get_bottom()[1]-self.height/2-.42 if under is not None else -.86
        start=LEFT*(config.frame_width/2+self.width/2)+UP*baseline
        end=RIGHT*(config.frame_width/2+self.width/2)+UP*baseline
        self.move_to(start)
        path=ParametricFunction(lambda t:start+t*(end-start)+UP*.18*math.sin(4*math.pi*t),t_range=[0,1])
        return Succession(FadeIn(self,run_time=.08),
            MoveAlongPath(self,path,rate_func=linear,run_time=2.15),FadeOut(self,run_time=.12))
