"""Reusable explanatory diagrams; scene authors supply content and meaning."""
import math
import numpy as np
from manim import (AnimationGroup,Axes,Create,DOWN,Dot,FadeIn,FadeOut,LEFT,Line,
    RIGHT,RoundedRectangle,Succession,Transform,UP,VGroup,VMobject,config,linear,Group,Brace)
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


class ObjectRow(Group):
    """A horizontal layout container; children retain their own identities."""
    _algovis_layout_container=True
    def __init__(self,*children,align_part=None,align_edge='top'):
        self.align_part=align_part
        if align_edge not in ('top','bottom'):raise ValueError('Object-row alignment is top or bottom')
        self.align_edge=align_edge
        super().__init__(*children)

    def apply_scene_typography(self,typography,*,group):
        for child in self:assign_scene_typography(child,typography,group=group)
        self.arrange(RIGHT,aligned_edge=UP,buff=.45)
        if self.align_part and len(self):
            anchor='get_top' if self.align_edge=='top' else 'get_bottom'
            y=getattr(getattr(self[0],self.align_part),anchor)()[1]
            for child in self:child.shift((0,y-getattr(getattr(child,self.align_part),anchor)()[1],0))

    def with_state(self,*,index,**state):
        children=[child.copy() for child in self]
        children[index]=children[index].with_state(**state)
        return ObjectRow(*children,align_part=self.align_part,align_edge=self.align_edge)


class BracedGroup(Group):
    """Related definitions keep their rows, common brace and explanatory label."""
    _algovis_layout_container=True
    def __init__(self,*rows,label,theme=DEFAULT_THEME):
        self.rows=list(rows)
        self.heading=LessonStyle(theme=theme).text(label,type_role='body',role='structure')
        self.brace=Brace(Group(*rows),LEFT,color=theme.foreground)
        super().__init__(*rows,self.heading,self.brace)

    def apply_scene_typography(self,typography,*,group):
        for row in self.rows:assign_scene_typography(row,typography,group=group)
        assign_scene_typography(self.heading,typography,group=group)
        block=Group(*self.rows).arrange(DOWN,aligned_edge=LEFT,buff=.35)
        self.brace.become(Brace(block,LEFT,color=self.brace.get_color()))
        self.heading.next_to(Group(block,self.brace),UP,buff=.35)


class FixedGrowthPlot(VGroup):
    """A fixed input axis. Curve drawing is separate from layout fitting.

    Intentional offscreen growth therefore never forces the surrounding scene
    to shrink or follow the curve. Labels keep their semantic type roles.
    """
    def __init__(self,*,function,label,x_label='input n',y_label=None,x_max=100,y_max=2400000,
                 x_ticks=(0,25,50,75,100),theme=DEFAULT_THEME):
        self.theme,self.function,self.y_max=theme,function,y_max
        self.x_ticks=tuple(x_ticks)
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
        self.x_title=style.text(x_label,type_role='label',role='muted')
        self.y_title=style.math(y_label or label,type_role='label',evaluation='bad')
        self.labels.add(self.x_title,self.y_title)
        self._place_labels(x_ticks)
        super().__init__(self.axes,self.labels)

    def _place_labels(self,x_ticks):
        for n,label in zip(x_ticks,self.labels[:len(x_ticks)]):label.next_to(self.axes.c2p(n,0),DOWN,buff=.12)
        for fraction,label in zip((1/3,2/3,1),self.labels[len(x_ticks):len(x_ticks)+3]):
            label.next_to(self.axes.c2p(0,self.y_max*fraction),LEFT,buff=.12)
        self.x_title.next_to(self.axes.x_axis.get_end(),DOWN,buff=.55)
        self.y_title.next_to(self.axes.y_axis.get_end(),UP,buff=.15)

    def apply_scene_typography(self,typography,*,group):
        for label in self.labels:
            if label not in (self.x_title,self.y_title):assign_scene_typography(label,typography,group=group,role='label')
        assign_scene_typography(self.x_title,typography,group=group,role='body')
        assign_scene_typography(self.y_title,typography,group=group,role='equation')

    def layout_in(self,width,height,typography):
        # Fit coordinate geometry, then place labels at their scene type size.
        # Scaling the entire plot would make its short y-axis title microscopic.
        x_ticks=self.x_ticks
        self.axes.stretch_to_fit_width(min(9.2,max(1.,width-1.5)))
        self.axes.stretch_to_fit_height(min(3.2,max(1.,height-1.2)))
        self._place_labels(x_ticks)
        for _ in range(3):
            self.axes.stretch_to_fit_width(max(1.,self.axes.width-max(0.,self.width-width)))
            self.axes.stretch_to_fit_height(max(1.,self.axes.height-max(0.,self.height-height)))
            self._place_labels(x_ticks)

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
        for label in [*self.x_labels,*self.y_labels]:
            assign_scene_typography(label,typography,group=group,role='label')
        for label in [self.y_title,*self.legend]:
            assign_scene_typography(label,typography,group=group,role='equation')

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

    def fill_width(self,width):
        """Stretch the illustration's footprint, preserving readable label type."""
        self[0].scale_to_fit_width(width)
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
    def __init__(self,count=5,*,known=(),dominoes=False,theme=DEFAULT_THEME):
        from manim import Arrow
        self.theme=theme
        self.cases=StateRow([rf'P({index})' for index in range(count)],theme=theme,gap=.55)
        from ..semantics import set_semantics
        for index in known:set_semantics(self.cases[index],status='computed',theme=theme)
        self.arrows=VGroup(*(Arrow(a.get_right(),b.get_left(),buff=.09,color=theme.muted,
            tip_length=.1,stroke_width=2) for a,b in zip(self.cases,self.cases[1:])))
        self.reserve_dominoes=bool(dominoes)
        super().__init__(self.arrows,self.cases)
        if self.reserve_dominoes:
            from manim import Rectangle
            self.motion_bounds=Rectangle(width=self.cases.width,height=self._domino_metrics()[1],
                stroke_opacity=0,fill_opacity=0).move_to(self.cases)
            self.add(self.motion_bounds)

    def apply_scene_typography(self,typography,*,group):
        self.cases.apply_scene_typography(typography,group=group)
        if self.reserve_dominoes:
            self.motion_bounds.stretch_to_fit_width(self.cases.width)
            self.motion_bounds.stretch_to_fit_height(self._domino_metrics()[1]).move_to(self.cases)

    def _domino_metrics(self):
        width=max(case.label.width for case in self.cases)+.24
        return width,max(1.5,2.1*width),.3*width

    def propagate(self,indices,*,trigger,reason):
        """One narrated implication process: recolor and visibly pulse each case.

        A plural phrase can advance several cases in sequence. Their internal
        phases belong to this one verified trigger, rather than invented words.
        """
        from manim import UpdateFromAlphaFunc,interpolate_color,there_and_back,ManimColor
        from ..semantics import set_semantics
        if not str(trigger).strip() or not str(reason).strip():
            raise ValueError('Correctness propagation needs its spoken trigger and purpose')
        indices=(indices,) if isinstance(indices,int) else tuple(indices)
        if not indices or any(not 0<=i<len(self.cases) for i in indices):
            raise ValueError('Name the cases whose correctness propagates')
        original={i:self.cases[i].copy() for i in indices}
        colors={i:self.cases[i].box.get_stroke_color() for i in indices}
        arrow_colors={i:self.arrows[i-1].get_color() for i in indices if i}
        success=ManimColor(self.theme.success)
        def update(_chain,alpha):
            for phase,index in enumerate(indices):
                progress=np.clip(alpha*len(indices)-phase,0,1)
                case=self.cases[index]
                scale=1+.14*there_and_back(progress)
                # Geometry and paint change as one component-owned process;
                # promoting an opaque cell background would cover its label.
                target=original[index].copy().scale(scale)
                case.box.set_points(target.box.get_points())
                for live,reference in zip(case.label.get_family(),target.label.get_family()):
                    if live.has_points():live.set_points(reference.get_points())
                case.box.set_stroke(interpolate_color(colors[index],success,progress))
                if index:self.arrows[index-1].set_color(interpolate_color(arrow_colors[index],success,progress))
                if progress>=1:set_semantics(case,status='computed',theme=self.theme)
        animation=UpdateFromAlphaFunc(self,update,rate_func=linear)
        animation._algovis_component_process=True
        animation._algovis_attention={'trigger':trigger,'reason':reason}
        animation._algovis_focus_target=self.cases[indices[0]] if len(indices)==1 else self.cases
        return animation

    def as_dominoes(self):
        from manim import Rectangle
        # The physical contact model and readable labels share one spacing.
        width,height,gap=self._domino_metrics()
        targets=VGroup(*(Rectangle(width=width,height=height,color=case.box.get_stroke_color(),
            fill_color=self.theme.surface,fill_opacity=1) for case in self.cases)).arrange(RIGHT,buff=gap).move_to(self.cases)
        self.geometry=DominoGeometry(width=width,height=height,gap=gap)
        cells=[]
        for case,target in zip(self.cases,targets):
            cell=case.copy();cell.box.become(target);cell.label.move_to(target);cells.append(cell)
        chain=self
        class ToDominoes(AnimationGroup):
            _algovis_component_process=True
            def finish(self):
                super().finish()
                chain.arrows.set_opacity(0)
            def clean_up_from_scene(self,scene):
                super().clean_up_from_scene(scene)
                # FadeOut restores its source paint. These semantic children
                # remain in the chain, so record the new hidden state as well.
                chain.arrows.set_opacity(0)
        # Move the complete cell. Independent box roots paint over their own
        # labels until a later component animation happens to reunite them.
        return ToDominoes(FadeOut(self.arrows),*(Transform(case,target) for case,target in zip(self.cases,cells)))

    def fall(self,front):
        from manim import UpdateFromAlphaFunc,DR,PI,smooth
        from ..layout import measured_font_size
        if not hasattr(self,'upright'):
            self.upright=[case.copy() for case in self.cases]
            self.pivots=[case.box.get_corner(DR) for case in self.upright]
        def update(_mob,alpha):
            limit=PI/2 if front==len(self.cases)-1 else self.geometry.first_contact
            angles=self.geometry.angles(len(self.cases),front,smooth(alpha)*limit)
            for index,(case,original,pivot,angle) in enumerate(zip(self.cases,self.upright,self.pivots,angles)):
                target=original.copy().rotate(-angle,about_point=pivot)
                case.box.become(target.box)
                case.label.become(target.label)
                for live,reference in zip(case.label.get_family(),original.label.get_family()):
                    if getattr(reference,'_algovis_font_reference',None) and live.height>0:
                        # Rotating an unchanged font changes its ink bounds,
                        # not its point size. Keep that distinction measured.
                        live._algovis_font_reference=(measured_font_size(reference),float(live.height))
                if index<=front:case.box.set_stroke(self.theme.success).set_fill(self.theme.success,opacity=.5)
        return UpdateFromAlphaFunc(self,update)
