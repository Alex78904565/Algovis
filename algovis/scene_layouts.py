"""Semantic scene locations with scene-owned geometry and typography."""
from manim import LEFT, Group
import numpy as np
from .composition import ColumnSlide, SlideView
from .fitting import FitArea
from .layout import ColumnLayout
from .presentation import SlideRegion


class CenteredScene(ColumnSlide):
    """A centered vertical stack, for a title or one compact argument."""
    def _arrange(self):
        super()._arrange()
        body=[item.target for item in self.items.values() if item.slot=='body']
        if body:
            stack=Group(*body)
            stack.move_to(self.layout.body.center)
            for part in body:part.set_x(self.layout.body.center[0])


class ListScene(ColumnSlide):
    """A left-aligned explanation whose rows grow from top to bottom."""


class SlotScene(SlideView):
    """A reusable arrangement exposes named regions, not per-object coordinates.

    Subclasses declare row/column proportions. Objects placed in a location
    receive the common scene type roles and are fitted/aligned inside it.
    Diagram components can reflow their own geometry to the available region.
    """
    ROWS=(('main',1),)
    COLUMNS=()
    diagram_slots=()
    centered_slots=()
    gutter=.35

    def _slots(self):
        body=self.layout.body
        if self.COLUMNS:
            columns=body.split_columns(*(weight for _,weight in self.COLUMNS),gutter=self.gutter)
            return dict(zip((key for key,_ in self.COLUMNS),columns))
        available=body.height-self.gutter*(len(self.ROWS)-1)
        total=sum(weight for _,weight in self.ROWS)
        top=body.center[1]+body.height/2
        regions={}
        for key,weight in self.ROWS:
            height=available*weight/total
            regions[key]=SlideRegion((body.center[0],top-height/2,0),body.width,height)
            top-=height+self.gutter
        return regions

    def add(self,name,value,*,slot='main',region=None,**options):
        slot=region or slot
        if slot not in self._slots() and slot not in ('header','footer'):
            raise ValueError(f'Unknown {type(self).__name__} location: {slot}')
        return super().add(name,value,region=slot,**options)

    def _region(self,slot):
        return self._slots().get(slot) or super()._region(slot)

    def _fit_and_arrange(self):
        for item in self.items.values():
            reflow=getattr(type(item.target),'layout_in',None)
            if reflow is not None:
                region=self._region(item.slot)
                reflow(item.target,region.width,region.height,self.typography)
        super()._fit_and_arrange()

    def _fit_areas(self):
        areas=[]
        for slot,region in self._slots().items():
            items=[item for item in self.items.values() if item.slot==slot]
            # Each diagram owns its geometric fit. Ordinary text shares a
            # fitting scale across locations, so peer rows retain their sizes.
            group=slot if slot in self.diagram_slots else 'body'
            areas.append(FitArea(group,items,region.width,region.height,
                                 stacked=True,gap=.28))
        areas.extend(area for area in super()._fit_areas() if area.group=='header')
        footer=[item for item in self.items.values() if item.slot=='footer']
        areas.append(FitArea('footer',footer,self.layout.footer.width,self.layout.footer.height,stacked=True,gap=.1))
        return areas

    def _arrange(self):
        for slot,region in self._slots().items():
            items=[(name,item) for name,item in self.items.items() if item.slot==slot]
            column=ColumnLayout(region,gap=.28)
            from .composition import _column_row
            for name,item in items:_column_row(column,name,item)
            if slot in self.centered_slots and items:
                group=Group(*(item.target for _,item in items))
                group.move_to(region.center)
                for _,item in items:item.target.set_x(region.center[0])
        footer=[(name,item) for name,item in self.items.items() if item.slot=='footer']
        if len(footer)>1:
            column=ColumnLayout(self.layout.footer,gap=.1)
            for name,item in footer:_column_row(column,name,item)
            Group(*(item.target for _,item in footer)).set_y(self.layout.footer.center[1])
        for item in self.items.values():
            if item.slot not in self._slots() and not (item.slot=='footer' and len(footer)>1):
                item.target.move_to(self.layout.region(item.slot).center)


class DiagramScene(SlotScene):
    ROWS=(('diagram',3),('explanation',1))
    diagram_slots=('diagram',)
    centered_slots=('diagram',)


class TreeScene(DiagramScene):
    ROWS=(('diagram',9),('explanation',1))


class DefinitionScene(DiagramScene):
    ROWS=(('diagram',1),('explanation',3))


class MapScene(SlotScene):
    """A centered concrete journey beneath its short instance definition."""
    ROWS=(('meaning',1),('map',3))
    diagram_slots=('map',)
    centered_slots=('map',)


class DerivationScene(SlotScene):
    ROWS=(('meaning',1),('equation',2),('explanation',1))


class RecurrenceScene(SlotScene):
    """Keep the function meaning, recurrence and base case visible together."""
    ROWS=(('meaning',1),('equation',2),('base',1.6),('explanation',.8))


class ComparisonScene(SlotScene):
    COLUMNS=(('left',1),('right',1))

    def definition_route(self,source,destination):
        """Carry cross-column values through the gutter if artwork intervenes."""
        start,end=source.get_center(),destination.get_center()
        slots=self._slots();left,right=slots['left'],slots['right']
        gutter=(left.center[0]+left.width/2+right.center[0]-right.width/2)/2
        if (start[0]-gutter)*(end[0]-gutter)>=0:return ()
        margin=max(source.width,destination.width)/2+.08
        vertical=max(source.height,destination.height)/2+.08
        samples=[start+(end-start)*a for a in np.linspace(0,1,61)]
        for item in self.items.values():
            if item.slot not in ('left','right'):continue
            if id(source) in {id(p) for p in item.object.mobject.get_family()}:continue
            if id(destination) in {id(p) for p in item.target.get_family()}:continue
            obstacle=item.target
            if any(obstacle.get_left()[0]-margin<p[0]<obstacle.get_right()[0]+margin
                   and obstacle.get_bottom()[1]-vertical<p[1]<obstacle.get_top()[1]+vertical
                   for p in samples):
                return (np.array([gutter,start[1],0]),np.array([gutter,end[1],0]))
        return ()


class ConversionScene(ComparisonScene):
    """Two representations with a connector between their principal rows.

    A heading/call stack uses its second row as the principal row. Costs may
    subsequently be added below either side without displacing the connector.
    """
    gutter=1.

    def _slots(self):
        regions=super()._slots()
        body=self.layout.body
        regions['connector']=SlideRegion(body.center,self.gutter,body.height)
        return regions

    def _arrange(self):
        super()._arrange()
        sides={}
        def row_anchor(target):
            if getattr(target,'_algovis_layout_container',False) and len(target)>1:
                target=target[1]
            return float(target.baseline) if hasattr(type(target),'baseline') else target.get_y()
        for slot in ('left','right'):
            items=[item for item in self.items.values() if item.slot==slot]
            for item in items:
                center=self._region(slot).center[0]
                item.target.set_x(center)
                if getattr(item.target,'_algovis_layout_container',False):
                    for row in item.target:row.set_x(center)
            sides[slot]=items
        for left,right in zip(sides['left'],sides['right']):
            baseline=min(row_anchor(left.target),row_anchor(right.target))
            for item in (left,right):item.target.shift((0,baseline-row_anchor(item.target),0))
        reference=next((items[0].target for items in sides.values() if items),None)
        if reference is not None:
            for item in self.items.values():
                if item.slot=='connector':
                    item.target.set_x(self.layout.body.center[0])
                    item.target.shift((0,row_anchor(reference)-row_anchor(item.target),0))


class AnalysisScene(SlotScene):
    """Retain the mathematical definition above two runtime derivations."""
    ROWS=(('definition',1.6),('comparison',4))

    def _slots(self):
        regions=super()._slots()
        left,right=regions.pop('comparison').split_columns(1,1,gutter=self.gutter)
        return {**regions,'left':left,'right':right}


class RecapScene(SlotScene):
    """Keep a numbered method beside its consequences, with room for a brace."""
    COLUMNS=(('steps',7.5),('consequences',5.5))


class StoryScene(SlotScene):
    ROWS=(('story',2),('equation',1))
    diagram_slots=('story',)
    centered_slots=('story',)


class TreeExplanationScene(SlotScene):
    ROWS=(('diagram',3.5),('equations',2.5))
    diagram_slots=('diagram',)
    centered_slots=('diagram',)


class TreeArrayScene(SlotScene):
    ROWS=(('diagram',4),('array',1))
    diagram_slots=('diagram','array')
    centered_slots=('diagram','array')
