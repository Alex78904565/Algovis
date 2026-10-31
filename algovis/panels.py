"""Recursive layout ownership, compiled to the one shared view renderer.

Panels are detached layout containers, never Manim drawing parents. A panel
owns named child positions; an object keeps its identity when reparented.
Only the global view transition decides which artwork moves, copies or retires.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import copy
from dataclasses import dataclass
from functools import wraps
import math

from manim import Group, UL

from .layout import ColumnLayout


@dataclass(frozen=True)
class PanelMeasure:
    width: float = 0.
    height: float = 0.


@dataclass
class PanelLeaf:
    """A named position, separate from the identity of its current occupant."""
    name: str
    value: object
    font_scale: float | None = None
    font_reason: str | None = None


@dataclass(frozen=True)
class PanelReservation:
    """Only a future size; it has no drawable object and no visual identity."""
    size: PanelMeasure


class Panel:
    """A common-edge column, centered as one block by default.

    ``add`` returns the object's stable handle. ``panel`` adds a nested layout
    container. Mount with ``PanelSlide.add_panel``; future states are ordinary
    detached slide forks. There are no per-object coordinates in this API.
    """
    layout_contract=None
    def __init_subclass__(cls,**kwargs):
        super().__init_subclass__(**kwargs)
        arrange=cls.__dict__.get('arrange')
        if arrange is not None:
            @wraps(arrange)
            def traced(self,*args,**kwargs):
                result=arrange(self,*args,**kwargs)
                self._record_arrangement(f'{cls.__module__}.{cls.__qualname__}.arrange')
                return result
            cls.arrange=traced

    def __init__(self, *, gap=.28, align='left', vertical='center', padding=0, center_block=True,
                 alignment_reason=None):
        if not math.isfinite(gap) or gap < 0 or not math.isfinite(padding) or padding < 0:
            raise ValueError('Panel gap and padding must be finite and nonnegative')
        if align not in ('left', 'center') or vertical not in ('top', 'center'):
            raise ValueError('Panel alignment must be left/center and top/center')
        if (not center_block or vertical!='center') and not alignment_reason:
            raise ValueError('A non-centered panel policy needs an explicit alignment_reason; missing measurements cannot disable centering')
        self.gap, self.align, self.vertical, self.padding = gap, align, vertical, padding
        self.center_block = bool(center_block)
        self.alignment_reason=alignment_reason
        self.children = OrderedDict()
        self.content_width = self.content_height = None
        self.reserve_future = True

    def _put(self, name, value):
        if not isinstance(name, str) or not name or '/' in name:
            raise ValueError('A panel position needs a nonempty name without slashes')
        if name in self.children:
            raise ValueError(f'Duplicate panel position: {name}')
        self.children[name] = value

    def add(self, name, value, *, font_scale=None, font_reason=None):
        from .composition import _object
        if isinstance(value, str):
            from .objects import TextObject
            value = TextObject(value)
            value._algovis_inherit_panel_theme=True
        handle = _object(value)
        self._put(name, PanelLeaf(name, handle,font_scale,font_reason))
        return handle

    def panel(self, name, child):
        if not isinstance(child, Panel):
            raise TypeError('A nested layout must be a Panel')
        if child is self or any(node is self for _, node in child.walk()):
            raise ValueError('Panels cannot contain a cycle')
        self._put(name, child)
        return child

    def fork(self):
        result = copy(self)
        result.children = OrderedDict((name, child.fork() if isinstance(child, Panel)
                                       else copy(child)) for name, child in self.children.items())
        return result

    def rebind(self, items, *, frame=None):
        """Snapshot structure without leaving references to an earlier target."""
        result=self.fork()
        for _,child in result.walk():
            if isinstance(child,PanelLeaf):child.value=items[child.name]
            elif frame is not None and hasattr(child,'frame'):child.frame=frame
        return result

    def walk(self, path=()):
        yield path, self
        for name, child in self.children.items():
            if isinstance(child, Panel):
                yield from child.walk((*path, name))
            else:
                yield (*path, name), child

    def leaves(self):
        for path, child in self.walk():
            if isinstance(child, PanelLeaf):
                yield path, child

    @classmethod
    def bound(cls, items, **options):
        """Shared scene recipes bind existing detached leaf placements."""
        result = cls(**options)
        result.reserve_future = False
        for name, placement in items:
            result.children[name] = PanelLeaf(name, placement)
        return result

    def _size(self, child):
        if isinstance(child, Panel):
            return child.measure()
        if isinstance(child, PanelReservation):
            scale=getattr(self,'_measure_scale',1.)
            return PanelMeasure(child.size.width*scale,child.size.height*scale)
        from .composition import SlideView
        item = child.value
        factor=getattr(self,'_measure_scale',item.fit_scale)/item.fit_scale
        return PanelMeasure(float(item.target.width)*factor, float(SlideView._height(item))*factor)

    def sizes(self):
        """Measure visible children and reserve hidden future positions as data."""
        order=getattr(self,'_reserved_order',tuple(self.children))
        reserved=getattr(self,'_reserved_sizes',{})
        scale=getattr(self,'_measure_scale',1.)
        result=[]
        for name in order:
            child=self.children.get(name)
            actual=self._size(child) if child is not None else PanelMeasure()
            future=reserved.get(name,PanelMeasure())
            result.append((name,child,PanelMeasure(max(actual.width,future.width*scale),
                                                 max(actual.height,future.height*scale))))
        return result

    def measure_at_scale(self, scale):
        prior=[]
        for _,node in self.walk():
            if isinstance(node,Panel):
                prior.append((node,getattr(node,'_measure_scale',None)))
                node._measure_scale=scale
        try:return self.measure()
        finally:
            for node,value in prior:
                if value is None:node.__dict__.pop('_measure_scale',None)
                else:node._measure_scale=value

    def measure(self):
        sizes = [size for _,_,size in self.sizes()]
        return PanelMeasure(max((size.width for size in sizes), default=0.)+2*self.padding,
                            sum(size.height for size in sizes)+self.gap*max(0, len(sizes)-1)+2*self.padding)

    def arrange(self, region):
        from .composition import _column_row
        from .presentation import SlideRegion
        size = self.measure()
        self._used_own_measure=True
        self._record_arrangement('algovis.panels.Panel.arrange',size)
        if size.height<=0:return
        width = (self.content_width or size.width-2*self.padding or None) if self.center_block else None
        height = self.content_height or size.height-2*self.padding or None
        column = ColumnLayout(region, padding=self.padding, gap=self.gap,
                              content_width=width,
                              content_height=height if self.vertical == 'center' else None)
        for name, child, measure in self.sizes():
            if child is None or isinstance(child,PanelReservation):
                column.reserve(name,max(measure.height,.001))
                continue
            if isinstance(child, Panel):
                column.reserve(name, max(measure.height, .001))
                top, reserved = column._slots[name]
                child.arrange(SlideRegion((column.left+column.width/2, top-reserved/2, region.center[2]),
                                         column.width, reserved))
            else:
                if hasattr(self,'_reserved_order'):
                    column.reserve(name,max(measure.height,.001))
                    column.place(name,child.value.target)
                    from .core.math_row import MathRow
                    from .frames import CaseEquation
                    item=child.value
                    if isinstance(item.target,(MathRow,CaseEquation)):
                        ascent=float(item.target.get_top()[1]-item.target.baseline)
                        item.target.shift((0,ascent-item.ascent,0))
                else:_column_row(column, name, child.value)
                if self.align == 'center':
                    child.value.target.set_x(region.center[0])

    def flatten(self):
        """One visible owner per object, independent of panel paths."""
        result = OrderedDict()
        owners = {}
        for path, leaf in self.leaves():
            item = leaf.value
            key = id(item.object.mobject)
            if key in owners:
                raise ValueError(f'Object has two panel owners: {owners[key]} and {"/".join(path)}; use copy()')
            owners[key] = '/'.join(path)
            if leaf.name in result:
                raise ValueError(f'Duplicate compiled object name: {leaf.name}')
            result[leaf.name] = item
        return result

    def next(self, event, contexts):
        """Propagate the resolved spoken word and globally matched placements."""
        delivered={}
        for child in self.children.values():
            if isinstance(child,Panel):
                steps=child.next(event,contexts)
            elif isinstance(child,PanelLeaf):
                handle=child.value.object;key=id(handle.mobject)
                # A component layout group may have been expanded into its
                # child identities by the global matcher. It is not a new root.
                keys=[key] if key in contexts else [id(part) for part in handle.mobject.get_family()[1:]
                                                     if id(part) in contexts]
                steps={}
                for owned in keys:
                    step=contexts[owned]
                    if step.event is not event:raise ValueError('Child received a different spoken event')
                    owner=step.destination.object if step.destination is not None else step.previous.object
                    prepared=owner.next(step)
                    from .composition import ObjectStep
                    if not isinstance(prepared,ObjectStep):raise TypeError('Object.next must return an ObjectStep')
                    if (prepared.event is not event or prepared.destination is not step.destination
                            or prepared.previous is not step.previous or prepared.source is not step.source
                            or prepared.relation!=step.relation):
                        raise ValueError('Object.next can customize motion, not its matched ownership or panel layout')
                    steps[owned]=prepared
            else:continue
            if set(delivered)&set(steps):raise ValueError('Object advanced through two panel owners')
            delivered.update(steps)
        return delivered

    def describe(self):
        return {'type': type(self).__name__, 'alignment': self.align,
                'vertical': self.vertical,
                'centerBlock':self.center_block,'alignmentReason':self.alignment_reason,
                'layoutPath':getattr(self,'_layout_path',None),
                'layoutContract':self.layout_contract,
                'measurement':getattr(self,'_layout_measurement',None),
                'usedOwnMeasurement':getattr(self,'_used_own_measure',False),
                'children': {name: child.describe() if isinstance(child, Panel) else
                             {'object': child.name} if isinstance(child,PanelLeaf) else
                             {'reservedOnly':True} for name, child in self.children.items()}}

    def _record_arrangement(self,path,size=None):
        size=size or self.measure()
        self._layout_path=path
        self._layout_measurement={'width':size.width,'height':size.height}


class CenterPanel(Panel):
    """An intrinsic diagram or a header, centered without a typography override."""
    def arrange(self, region):
        values = list(self.children.values())
        if any(isinstance(child, Panel) for child in values):
            raise TypeError('Use a column panel for nested content')
        targets = [child.value.target for child in values]
        if not targets:
            return
        Group(*targets).move_to(region.center)
        for target in targets:
            target.set_x(region.center[0])


class CenteredColumnPanel(Panel):
    """Center an intrinsic stack's ink, preserving its internal baselines."""
    def arrange(self, region):
        super().arrange(region)
        targets = [leaf.value.target for _,leaf in self.leaves()]
        if targets:
            Group(*targets).move_to(region.center)
            for target in targets:target.set_x(region.center[0])


class FooterPanel(Panel):
    """Center a common-edge footer vertically, preserving horizontal alignment."""
    def arrange(self, region):
        super().arrange(region)
        targets=[leaf.value.target for _,leaf in self.leaves()]
        if targets:Group(*targets).set_y(region.center[1])


class FrameRowPanel(Panel):
    """A semantic equation/proof position owned by the shared frame policy."""
    def __init__(self, frame):
        super().__init__()
        self.frame = frame

    def arrange(self, region):
        from .composition import _frame_row
        for _,leaf in self.leaves():_frame_row(self.frame,leaf.value)


class FixedPanel(Panel):
    """Component-owned chrome: retain intrinsic geometry without repositioning."""
    def arrange(self, region):
        pass


class PairedColumnPanel(Panel):
    """One paired column owns its rows, using the parent's shared row envelope."""
    def __init__(self,*,pairs,heights,**kwargs):
        super().__init__(**kwargs)
        self.pairs,self.heights=tuple(pairs),dict(heights)

    def arrange(self,region):
        from .core.proof import first_line_of
        planned={name for pair in self.pairs for name in pair}
        if set(self.children)-planned:
            raise ValueError('Paired column has objects without a planned row: '+', '.join(sorted(set(self.children)-planned)))
        column=ColumnLayout(region,padding=0,gap=.28,
            content_height=sum(self.heights.values())+.28*max(0,len(self.heights)-1))
        for index,pair in enumerate(self.pairs):
            column.reserve(str(index),self.heights[str(index)])
            for name in pair:
                if name not in self.children:continue
                item=self.children[name].value
                column.place(str(index),item.target)
                top=column._slots[str(index)][0]
                item.target.shift((0,top-first_line_of(item.target).get_top()[1],0))


class PairedPanel(Panel):
    """Corresponding rows in nested columns share their first readable line."""
    def __init__(self, *, pairs, heights, widths, gap=.35):
        super().__init__(gap=gap)
        self.pairs,self.heights,self.widths=tuple(pairs),dict(heights),dict(widths)
        self.allocated_regions={}

    def arrange(self, region):
        from .presentation import SlideRegion
        total_width=sum(self.widths.values())+self.gap
        left=region.center[0]-total_width/2
        self.allocated_regions={}
        for slot,child in self.children.items():
            if not isinstance(child,PairedColumnPanel):
                raise TypeError('PairedPanel requires PairedColumnPanel owners; direct child placement is removed')
            width=self.widths[slot]
            area=SlideRegion((left+width/2,region.center[1],0),max(width,.01),region.height)
            self.allocated_regions[slot]=area
            child.arrange(area)
            left+=width+self.gap


class ConversionPanel(Panel):
    """A centered call on each side with a baseline-aligned connector."""
    def __init__(self, regions):
        super().__init__()
        self.regions=dict(regions)

    def arrange(self, region):
        for name,child in self.children.items():child.arrange(self.regions[name])
        sides={}
        def row_anchor(target):
            if getattr(target,'_algovis_layout_container',False) and len(target)>1:target=target[1]
            return float(target.baseline) if hasattr(type(target),'baseline') else target.get_y()
        for slot in ('left','right'):
            leaves=[leaf.value for _,leaf in self.children[slot].leaves()]
            for item in leaves:
                center=self.regions[slot].center[0];item.target.set_x(center)
                if getattr(item.target,'_algovis_layout_container',False):
                    for row in item.target:row.set_x(center)
            sides[slot]=leaves
        for left,right in zip(sides['left'],sides['right']):
            baseline=min(row_anchor(left.target),row_anchor(right.target))
            for item in (left,right):item.target.shift((0,baseline-row_anchor(item.target),0))
        reference=next((items[0].target for items in sides.values() if items),None)
        if reference is not None and 'connector' in self.children:
            for _,leaf in self.children['connector'].leaves():
                leaf.value.target.set_x(region.center[0])
                leaf.value.target.shift((0,row_anchor(reference)-row_anchor(leaf.value.target),0))


class RegionPanel(Panel):
    """Slide recipe: allocate safe named regions to child layout owners."""
    def __init__(self):
        super().__init__(gap=0)
        self.regions = {}

    def in_region(self, name, region, child):
        self.panel(name, child)
        self.regions[name] = region
        return child

    def fork(self):
        result = super().fork()
        result.regions = self.regions.copy()
        return result

    def arrange(self, region=None):
        for name, child in self.children.items():
            child.arrange(self.regions[name])


class ProofStagePanel(Panel):
    """A proof stage owns its label and its first-line-aligned expression."""
    def __init__(self, frame, content, label, *, label_y=None):
        super().__init__()
        self.frame,self.content,self.label,self.label_y=frame,content,label,label_y
        for pair in (content,label):
            if pair is not None:self.children[pair[0]]=PanelLeaf(*pair)

    def arrange(self, region):
        from .composition import _frame_row
        from .core.proof import first_line_of
        if self.content is not None:_frame_row(self.frame,self.content[1])
        if self.label is not None:
            name,item=self.label
            key=item.slot[6:].upper().replace('_',' ')
            target=(self.frame.label_target(self.content[1].slot,first_line_of(self.content[1].target))
                    if self.content is not None else self.frame.labels_by_name[key].copy().set_y(
                        self.label_y if self.label_y is not None else self.frame.rows[key]))
            item.target.become(target)


class ProofRailPanel(FixedPanel):
    def __init__(self, frame):
        super().__init__()
        self.frame=frame

    def arrange(self, region):
        for _,leaf in self.leaves():
            leaf.value.target.put_start_and_end_on(
                [self.frame.divider.get_x(),region.center[1]+region.height/2,0],
                [self.frame.divider.get_x(),region.center[1]-region.height/2,0])


class ProofPanel(RegionPanel):
    """Shared proof owner: measured stages, rail, conclusion and continuation."""
    @staticmethod
    def plan_rows(frame, body, items, metrics, scale, gap):
        from .presentation import SlideRegion
        from .core.math_row import MathRow
        heights={slot:row['height']*scale for slot,row in metrics.items()}
        available=body.height-gap*(len(metrics)-1)
        ratio=min(1.,available/sum(heights.values()))
        top=body.center[1]+body.height/2
        left=frame.left[0];width=body.center[0]+body.width/2-left
        regions={}
        for slot in metrics:
            height=heights[slot]*ratio;y=top-height/2;frame.rows[slot]=y
            row=next((item for item in items.values() if item.slot==slot),None)
            if row is not None and isinstance(row.target,MathRow):
                ascent=metrics[slot]['ascent']*scale;descent=metrics[slot]['descent']*scale
                if (slot=='work' or metrics[slot].get('landing',0)) and height>ascent+descent+.1:
                    frame.rows[slot]=top-ascent-row.baseline_offset
                else:frame.rows[slot]-=row.baseline_offset+(ascent-descent)/2
            regions[slot]=SlideRegion((left+width/2,y,0),width,height)
            top-=height+gap
        return regions

    def arrange(self, region=None):
        from .core.math_row import MathRow
        super().arrange(region)
        leaves=self.flatten()
        if 'work' in leaves and 'inductive_step' in leaves:
            work=leaves['work'].target;step=leaves['inductive_step'].target
            if (isinstance(work,MathRow) and isinstance(step,MathRow)
                    and 'eq' in work.parts and 'eq' in step.parts and 'call' not in work.parts):
                work.shift((step.part('eq').get_left()[0]-work.part('eq').get_left()[0],0,0))


class AnalysisPanel(RegionPanel):
    """Derivation columns and result columns use the same centered left edges."""
    def __init__(self, widths, *, gap=.35):
        super().__init__()
        self.widths,self.gap=dict(widths),gap
        self.allocated_regions={}

    def arrange(self, region):
        from .presentation import SlideRegion
        super().arrange(region)
        left=region.center[0]-(sum(self.widths.values())+self.gap)/2
        self.allocated_regions={}
        for side in ('left','right'):
            width=self.widths[side]
            for slot in (side,side+'_result'):
                area=self.regions[slot]
                self.allocated_regions[slot]=SlideRegion((left+width/2,area.center[1],0),max(width,.01),area.height)
                for _,leaf in self.children[slot].leaves():
                    leaf.value.target.shift((left-leaf.value.target.get_left()[0],0,0))
            left+=width+self.gap


class RowPanel(Panel):
    """Nested side-by-side blocks, centered together with a common top."""
    def measure(self):
        sizes = [size for _,_,size in self.sizes()]
        return PanelMeasure(sum(size.width for size in sizes)+self.gap*max(0,len(sizes)-1)+2*self.padding,
                            max((size.height for size in sizes),default=0.)+2*self.padding)

    def arrange(self, region):
        from .presentation import SlideRegion
        size = self.measure()
        self._used_own_measure=True
        if size.height<=0:return
        width = self.content_width or size.width-2*self.padding
        height = self.content_height or size.height-2*self.padding
        if width > region.width+1e-7 or height > region.height+1e-7:
            raise ValueError('Row panel exceeds its allocated space')
        x = region.center[0]-width/2
        top = region.center[1]+height/2 if self.vertical == 'center' else region.center[1]+region.height/2-self.padding
        for _,child,measure in self.sizes():
            if child is None or isinstance(child,PanelReservation):
                x+=measure.width+self.gap
                continue
            area = SlideRegion((x+measure.width/2,top-height/2,region.center[2]),max(measure.width,.001),height)
            if isinstance(child, Panel):
                child.arrange(area)
            else:
                child.value.target.move_to((x,top,region.center[2]),aligned_edge=UL)
            x += measure.width+self.gap


class PanelFitArea:
    """Fit all nested content together while keeping layout gaps unscaled."""
    def __init__(self, group, panel, region):
        self.group,self.panel,self.region=group,panel,region
        self.items=[leaf.value for _,leaf in panel.leaves()]
        self.width,self.height=region.width,region.height

    def scale(self, _heights):
        def fits(scale):
            size=self.panel.measure_at_scale(scale)
            return size.width<=self.width+1e-9 and size.height<=self.height+1e-9
        if fits(1.):return 1.
        low,high=0.,1.
        for _ in range(48):
            middle=(low+high)/2
            if fits(middle):low=middle
            else:high=middle
        return low


def plan_panel_envelopes(views):
    """Reserve named positions across a complete explanation, never live ink."""
    from .composition import SlideView
    sizes={};orders={};templates={}
    for view in views:
        for root_name,panel in view._bound_author_panels().items():
            for path,node in panel.walk((root_name,)):
                if isinstance(node,Panel):
                    templates.setdefault(path,node.fork())
                    order=orders.setdefault(path,[])
                    # Preserve authored order; insert a new position before its
                    # next already-known neighbor rather than appending blindly.
                    names=list(node.children)
                    for index,name in enumerate(names):
                        if name not in order:
                            successor=next((n for n in names[index+1:] if n in order),None)
                            order.insert(order.index(successor) if successor else len(order),name)
                else:
                    item=node.value
                    old=sizes.get(path,PanelMeasure())
                    sizes[path]=PanelMeasure(max(old.width,float(item.target.width)),
                        max(old.height,float(SlideView._height(item))))
    return {'sizes':sizes,'orders':orders,'templates':templates}


def apply_panel_envelopes(panel, envelope, path, *, scale=1.):
    def reserve(node,path):
        for name in envelope['orders'].get(path,node.children):
            child_path=(*path,name)
            if name not in node.children:
                if child_path in envelope['templates']:
                    template=envelope['templates'][child_path]
                    child=copy(template);child.children=OrderedDict()
                    node.children[name]=child
                else:
                    node.children[name]=PanelReservation(envelope['sizes'].get(child_path,PanelMeasure()))
            if isinstance(node.children[name],Panel):reserve(node.children[name],child_path)
    reserve(panel,path)
    for local,node in panel.walk(path):
        if isinstance(node,Panel):
            node._reserved_order=tuple(envelope['orders'].get(local,node.children))
            node._reserved_sizes={name:envelope['sizes'].get((*local,name),PanelMeasure())
                                  for name in node._reserved_order}
            node._measure_scale=scale


def arrange_view(view, root):
    """All scene recipes enter the same recursive layout/ownership boundary."""
    leaves = root.flatten()
    if set(leaves) != set(view.items):
        raise ValueError('A panel recipe must own every visible object exactly once')
    if any(leaves[name] is not item for name,item in view.items.items()):
        raise ValueError('A panel recipe cannot substitute detached placement records')
    for _,node in root.walk():
        if isinstance(node,Panel):
            node._layout_path=None;node._layout_measurement=None;node._used_own_measure=False
    root.arrange()
    for path,node in root.walk():
        if isinstance(node,Panel) and node.flatten() and not node._layout_path:
            raise RuntimeError('Panel layout path was not executed at '+('/'.join(path) or '<root>')+'; remove the legacy placement bypass')
    errors=layout_path_errors(root.describe())
    if errors:raise RuntimeError('Panel layout migration required: '+str(errors[0]))
    view.panels = root
    view._allocated_panel_regions={}
    for _,node in root.walk():
        if isinstance(node,Panel):view._allocated_panel_regions.update(getattr(node,'allocated_regions',{}))


def layout_path_errors(tree):
    """One contract for runtime layout, tests and pre-publication inspection."""
    errors=[]
    def has_content(node):
        return 'object' in node or any(has_content(child) for child in node.get('children',{}).values())
    def inspect(node,path):
        if 'type' not in node:return
        if has_content(node):
            executed=node.get('layoutPath') or ''
            registered=executed.startswith('algovis.panels.') or bool(node.get('layoutContract'))
            if not executed or not registered or not node.get('measurement'):
                errors.append({'kind':'panel_layout_path_not_executed','path':path,'layoutPath':executed})
            if (not node.get('centerBlock',True) or node.get('vertical')=='top') and not node.get('alignmentReason'):
                errors.append({'kind':'unexplained_panel_alignment_override','path':path})
            if node.get('type') in ('Panel','RowPanel','CenteredColumnPanel','FooterPanel') and not node.get('usedOwnMeasurement'):
                errors.append({'kind':'panel_measurement_bypassed','path':path})
        for name,child in node.get('children',{}).items():inspect(child,path+'/'+name)
    inspect(tree,'<root>')
    return errors
