"""Reusable explanatory diagrams; scene authors supply content and meaning."""
import math
import numpy as np
from manim import (AnimationGroup,Axes,Create,DOWN,Dot,FadeIn,FadeOut,LEFT,Line,
    RIGHT,RoundedRectangle,Succession,Transform,UP,VGroup,VMobject,config,linear)
from ..layout import LessonStyle,assign_scene_typography
from ..theme import DEFAULT_THEME
from ..semantics import SemanticChange
from .structures import StateRow
from .dominoes import DominoGeometry


class MathStack(VGroup):
    """Related lines with one left edge and common scene typography."""
    _algovis_layout_container=True
    def __init__(self,*rows,theme=DEFAULT_THEME):
        self.theme=theme
        super().__init__(*rows)
        # Arrange only the detached scene target in apply_scene_typography.
        # Rows may already be visible objects being regrouped into this stack.

    def apply_scene_typography(self,typography,*,group):
        center=self.get_center()
        for row in self:assign_scene_typography(row,typography,group=group)
        self.arrange(DOWN,aligned_edge=LEFT,buff=.25).move_to(center)

    def part(self,name):return self[int(name)]

    def with_state(self,*,rows):
        return MathStack(*(row.copy() for row in rows),theme=self.theme).arrange(
            DOWN,aligned_edge=LEFT,buff=.25).move_to(self)


class FixedGrowthPlot(VGroup):
    """A fixed input axis. Curve drawing is separate from layout fitting.

    Intentional offscreen growth therefore never forces the surrounding scene
    to shrink or follow the curve. Labels keep their semantic type roles.
    """
    def __init__(self,*,function,label,x_max=100,y_max=2400000,
                 x_ticks=(0,25,50,75,100),theme=DEFAULT_THEME):
        self.theme,self.function,self.y_max=theme,function,y_max
        self.axes=Axes(x_range=[0,x_max,max(1,x_max/4)],y_range=[0,y_max,y_max/3],
            x_length=9.2,y_length=3.2,tips=False,
            axis_config={'color':theme.muted,'stroke_width':1.5,'tick_size':.045})
        style=LessonStyle(theme=theme)
        self.labels=VGroup(*(style.math(str(n),type_role='label',role='muted').next_to(
            self.axes.c2p(n,0),DOWN,buff=.12) for n in x_ticks))
        for fraction in (1/3,2/3,1):
            value=round(y_max*fraction)
            self.labels.add(style.math(f'{value:,}'.replace(',','{,}'),type_role='label',role='muted')
                .next_to(self.axes.c2p(0,value),LEFT,buff=.12))
        self.labels.add(style.text('input n',type_role='label',role='muted').next_to(self.labels[4],DOWN,buff=.15))
        self.labels.add(style.math(label,type_role='label',evaluation='bad').next_to(self.axes.y_axis.get_end(),UP,buff=.15))
        super().__init__(self.axes,self.labels)

    def apply_scene_typography(self,typography,*,group):
        for label in self.labels:assign_scene_typography(label,typography,group=group,role='label')

    def draw_growth(self):
        limit=config.frame_height/2+.15
        last_y=self.axes.p2c([self.axes.get_x(),limit,0])[1]
        end=0.
        while self.function(end)<last_y and end<100:end+=.05
        curve=VMobject(color=self.theme.danger,stroke_width=4)
        curve.set_points_smoothly([self.axes.c2p(x,self.function(x)) for x in np.linspace(0,end,180)])
        return Create(curve,rate_func=linear)


class LogRuntimeComparison(VGroup):
    """Fixed log10 axes and labelled operation-count curves."""
    def __init__(self,series,*,x_max=20,y_max=20,theme=DEFAULT_THEME):
        self.theme=theme
        self.x_max,self.y_max=x_max,y_max
        self.axes=Axes(x_range=[2,x_max,2],y_range=[0,y_max,1],x_length=9.2,y_length=3.6,
            tips=False,axis_config={'color':theme.muted,'stroke_width':1.5})
        style=LessonStyle(theme=theme)
        self.x_labels=VGroup(*(style.math(str(x),type_role='label',role='muted').next_to(
            self.axes.c2p(x,0),DOWN,buff=.12) for x in range(2,x_max+1,4)))
        self.y_labels=VGroup(*(style.math(str(y),type_role='label',role='muted').next_to(
            self.axes.c2p(2,y),LEFT,buff=.12) for y in range(4,y_max+1,4)))
        self.y_title=style.math(r'\log_{10}(\text{operations})',type_role='label').next_to(self.axes,UP,buff=.22)
        self.curves=VGroup();self.legend=VGroup()
        for label,function,evaluation in series:
            self.curves.add(self.axes.plot(function,x_range=[2,x_max],color=theme.role_color(evaluation),stroke_width=3))
            self.legend.add(style.math(label,type_role='label',evaluation=evaluation))
        self.legend.arrange(RIGHT,buff=.65).next_to(self.axes,DOWN,buff=.55)
        super().__init__(self.axes,self.x_labels,self.y_labels,self.y_title,self.legend,self.curves)
        self.curves.set_opacity(0)
        self.y_title.set_opacity(0)

    def apply_scene_typography(self,typography,*,group):
        for label in [*self.x_labels,*self.y_labels,self.y_title,*self.legend]:
            assign_scene_typography(label,typography,group=group,role='label')

    def layout_in(self,width,height,typography):
        """Fit the axes rather than shrinking their labels with the drawing."""
        # The caller assigns label typography first. All later reflows retain
        # those glyph sizes; only coordinate geometry and curve points change.
        old_axes=self.axes.copy()
        curve_points=[curve.points.copy() for curve in self.curves]
        self.axes.stretch_to_fit_width(min(9.2,max(1.,width-.8)))
        self.axes.stretch_to_fit_height(min(3.6,max(1.,height-1.4)))
        def labels():
            for curve,points in zip(self.curves,curve_points):
                curve.set_points(np.array([self.axes.c2p(*old_axes.p2c(point)) for point in points]))
            for x,label in zip(range(2,self.x_max+1,4),self.x_labels):
                label.next_to(self.axes.c2p(x,0),DOWN,buff=.12)
            for y,label in zip(range(4,self.y_max+1,4),self.y_labels):
                label.next_to(self.axes.c2p(2,y),LEFT,buff=.12)
            self.y_title.next_to(self.axes,UP,buff=.22)
            self.legend.arrange(RIGHT,buff=.65).next_to(self.axes,DOWN,buff=.55)
        labels()
        # Hidden title/curves reserve their future geometry as well.
        for _ in range(2):
            self.axes.stretch_to_fit_width(max(1.,self.axes.width-max(0.,self.width-width)))
            self.axes.stretch_to_fit_height(max(1.,self.axes.height-max(0.,self.height-height)))
            labels()

    def draw_series(self):
        self.curves.set_stroke(opacity=1).set_fill(opacity=0)
        return AnimationGroup(*(Create(curve) for curve in self.curves),lag_ratio=0)

    def explain_scale(self):
        self.y_title.set_opacity(1)
        return FadeIn(self.y_title)


class ServerRacks(VGroup):
    """A compact computer illustration with a readable semantic label."""
    def __init__(self,label,*,theme=DEFAULT_THEME):
        racks=VGroup()
        for _ in range(5):
            shell=RoundedRectangle(width=.55,height=1.5,corner_radius=.05,
                color=theme.primary,fill_color=theme.surface,fill_opacity=1,stroke_width=1.4)
            slots=VGroup(*(RoundedRectangle(width=.4,height=.13,corner_radius=.02,
                color=theme.muted,stroke_width=1) for _ in range(7))).arrange(DOWN,buff=.045).move_to(shell)
            lights=VGroup(*(Dot(slot.get_right()+LEFT*.05,radius=.01,color=theme.success) for slot in slots))
            racks.add(VGroup(shell,slots,lights))
        racks.arrange(RIGHT,buff=.08)
        self.label=LessonStyle(theme=theme).text(label,type_role='label',role='structure').next_to(racks,DOWN,buff=.22)
        super().__init__(racks,self.label)

    def apply_scene_typography(self,typography,*,group):
        assign_scene_typography(self.label,typography,group=group,role='label')
        self.label.next_to(self[0],DOWN,buff=.22)


class Worksheet(VGroup):
    """A written page that can literally be discarded, without warning flashes."""
    def __init__(self,title,rows,*,theme=DEFAULT_THEME):
        style=LessonStyle(theme=theme)
        self.content=MathStack(style.text(title,type_role='label'),*rows,theme=theme)
        self.paper=RoundedRectangle(width=self.content.width+.8,height=self.content.height+.7,
            corner_radius=.1,color=theme.foreground,fill_color=theme.surface,fill_opacity=1)
        super().__init__(self.paper,self.content)

    def apply_scene_typography(self,typography,*,group):
        self.content.apply_scene_typography(typography,group=group)
        self.paper.stretch_to_fit_width(self.content.width+.8).stretch_to_fit_height(self.content.height+.7).move_to(self.content)

    def discard(self):return FadeOut(self,shift=RIGHT*2.2,scale=.55)


class TreeAnnotation(VGroup):
    """Local notes belong beside their node, with a small relationship leader."""
    def __init__(self,node,content,*,side='left',theme=DEFAULT_THEME):
        if side not in ('left','right'):raise ValueError('A tree note needs a left or right side')
        self.node,self.content,self.side=node,content,side
        direction=LEFT if side=='left' else RIGHT
        content.next_to(node,direction,buff=.3)
        self.leader=Line(node.get_edge_center(direction),content.get_edge_center(-direction),
                         color=content.get_color(),stroke_width=1)
        super().__init__(self.leader,content)

    def apply_scene_typography(self,typography,*,group):
        assign_scene_typography(self.content,typography,group=group,role='note')
        direction=LEFT if self.side=='left' else RIGHT
        self.content.next_to(self.node,direction,buff=.3)
        self.leader.put_start_and_end_on(self.node.get_edge_center(direction),self.content.get_edge_center(-direction))


class InductionChain(VGroup):
    """The same case boxes can become a contact-driven domino chain."""
    def __init__(self,count=5,*,theme=DEFAULT_THEME):
        from manim import Arrow
        self.theme=theme
        self.cases=StateRow([rf'P({index})' for index in range(count)],theme=theme,gap=.55)
        self.arrows=VGroup(*(Arrow(a.get_right(),b.get_left(),buff=.09,color=theme.muted,
            tip_length=.1,stroke_width=2) for a,b in zip(self.cases,self.cases[1:])))
        super().__init__(self.arrows,self.cases)

    def apply_scene_typography(self,typography,*,group):
        self.cases.apply_scene_typography(typography,group=group)

    def propagate(self,index):
        animations=[SemanticChange(self.cases[index],status='computed',theme=self.theme)]
        if index:animations.append(self.arrows[index-1].animate.set_color(self.theme.success))
        return AnimationGroup(*animations)

    def as_dominoes(self):
        from manim import Rectangle
        targets=VGroup(*(Rectangle(width=.42,height=1.3,color=self.theme.primary,
            fill_color=self.theme.surface,fill_opacity=1) for _ in self.cases)).arrange(RIGHT,buff=.25).move_to(self.cases)
        self.geometry=DominoGeometry(width=.42,height=1.3,gap=.25)
        chain=self
        class ToDominoes(AnimationGroup):
            _algovis_component_process=True
            def finish(self):
                super().finish()
                chain.arrows.set_opacity(0)
                for case in chain.cases:case.label.set_opacity(0)
            def clean_up_from_scene(self,scene):
                super().clean_up_from_scene(scene)
                # FadeOut restores its source paint. These semantic children
                # remain in the chain, so record the new hidden state as well.
                chain.arrows.set_opacity(0)
                for case in chain.cases:case.label.set_opacity(0)
        return ToDominoes(FadeOut(self.arrows),*(FadeOut(case.label) for case in self.cases),
            *(Transform(case.box,target) for case,target in zip(self.cases,targets)))

    def fall(self,front):
        from manim import UpdateFromAlphaFunc,DR,PI,smooth
        if not hasattr(self,'upright'):
            self.upright=[case.box.copy() for case in self.cases]
            self.pivots=[box.get_corner(DR) for box in self.upright]
        def update(_mob,alpha):
            limit=PI/2 if front==len(self.cases)-1 else self.geometry.first_contact
            angles=self.geometry.angles(len(self.cases),front,smooth(alpha)*limit)
            for index,(case,original,pivot,angle) in enumerate(zip(self.cases,self.upright,self.pivots,angles)):
                case.box.become(original.copy().rotate(-angle,about_point=pivot))
                if index<=front:case.box.set_stroke(self.theme.success).set_fill(self.theme.success,opacity=.5)
        return UpdateFromAlphaFunc(self,update)
