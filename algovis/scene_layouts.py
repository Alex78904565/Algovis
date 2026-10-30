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


class BlockScene(ColumnSlide):
    """One compact argument, centered as a block with internally aligned rows."""
    def block_widths(self):
        return {'BlockScene/body':max((item.target.width for item in self.items.values()
                                     if item.slot=='body'),default=0.)}

    def block_heights(self):
        rows=[item for item in self.items.values() if item.slot=='body']
        return {'BlockScene/body':sum(self._height(item) for item in rows)+self.gap*max(0,len(rows)-1)}

    def _arrange(self):
        widths=self.block_widths();widths.update(getattr(self,'_sequence_block_widths',{}))
        heights=self.block_heights();heights.update(getattr(self,'_sequence_block_heights',{}))
        column=ColumnLayout(self.layout.body,gap=self.gap,
            content_width=widths['BlockScene/body'] or None,
            content_height=heights['BlockScene/body'] or None)
        from .composition import _column_row
        for name,item in self.items.items():
            if item.slot=='body':_column_row(column,name,item)
            else:item.target.move_to(self.layout.region(item.slot).center)


class ListScene(BlockScene):
    """A growing list with common left edges in a centered argument block.

    Row alignment does not authorize anchoring the whole argument to a screen
    corner. This uses exactly the same reservation policy as BlockScene.
    """


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
    block_slots=()
    shared_block_height=True
    gutter=.35

    def __init__(self,*args,center_blocks=False,**kwargs):
        self._width_fill=frozenset()
        self.center_blocks=bool(center_blocks)
        if center_blocks:
            self.block_slots=tuple(key for key,_ in self.COLUMNS)
        super().__init__(*args,**kwargs)

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

    def add(self,name,value,*,slot='main',region=None,fill=None,**options):
        slot=region or slot
        if slot not in self._slots() and slot not in ('header','footer'):
            raise ValueError(f'Unknown {type(self).__name__} location: {slot}')
        if fill not in (None,'width'):raise ValueError('A slot can fill its width or use its natural size')
        old=self._width_fill
        if fill:
            if not hasattr(type(getattr(value,'planned_mobject',value)),'fill_width'):
                raise TypeError('Width filling needs component-owned geometry; it cannot stretch text')
            self._width_fill=old|{name}
        try:return super().add(name,value,region=slot,**options)
        except Exception:
            self._width_fill=old
            raise

    def _region(self,slot):
        return self._slots().get(slot) or super()._region(slot)

    def _fit_and_arrange(self):
        for item in self.items.values():
            reflow=getattr(type(item.target),'layout_in',None)
            if reflow is not None:
                region=self._region(item.slot)
                reflow(item.target,region.width,region.height,self.typography)
        for name in self._width_fill & self.items.keys():
            item=self.items[name];key=f'{type(self).__name__}/{item.slot}'
            peers=[peer.target.width for other,peer in self.items.items()
                   if peer.slot==item.slot and other not in self._width_fill]
            width=getattr(self,'_sequence_fill_widths',{}).get(key,max(peers,default=self._region(item.slot).width))
            item.target.fill_width(width)
        super()._fit_and_arrange()

    def fill_widths(self):
        return {f'{type(self).__name__}/{slot}':max((item.target.width
            for name,item in self.items.items() if item.slot==slot and name not in self._width_fill),default=0.)
            for slot in {self.items[name].slot for name in self._width_fill & self.items.keys()}}

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

    def block_widths(self):
        """Fitted widths of left-aligned blocks centered inside their regions.

        Internal row alignment and the position of the entire block are
        separate constraints. SceneSequence reserves the widest later block
        so adding a line cannot move the already-visible rows horizontally.
        """
        return {f'{type(self).__name__}/{slot}':max(
            (item.target.width for item in self.items.values() if item.slot==slot),
            default=0.) for slot in self.block_slots}

    def block_heights(self):
        heights={}
        for slot in self.block_slots:
            rows=[item for item in self.items.values() if item.slot==slot]
            heights[f'{type(self).__name__}/{slot}']=sum(self._height(item) for item in rows)+.28*max(0,len(rows)-1)
        if self.center_blocks and self.shared_block_height and heights:
            heights={key:max(heights.values()) for key in heights}
        return heights

    def _arrange(self):
        widths=self.block_widths()
        widths.update(getattr(self,'_sequence_block_widths',{}))
        heights=self.block_heights()
        heights.update(getattr(self,'_sequence_block_heights',{}))
        for slot,region in self._slots().items():
            items=[(name,item) for name,item in self.items.items() if item.slot==slot]
            width=widths.get(f'{type(self).__name__}/{slot}')
            height=heights.get(f'{type(self).__name__}/{slot}')
            column=ColumnLayout(region,gap=.28,content_width=width or None,content_height=height or None)
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
    block_slots=('explanation',)


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
    block_slots=('meaning','equation','explanation')


class RecurrenceScene(SlotScene):
    """Keep the function meaning, recurrence and base case visible together."""
    ROWS=(('meaning',1),('equation',2),('base',1.6),('explanation',.8))
    block_slots=('meaning','equation','base','explanation')


class ComparisonScene(SlotScene):
    """Two corresponding columns in a vertically centered argument block."""
    COLUMNS=(('left',1),('right',1))

    def __init__(self,*args,center_blocks=True,**kwargs):
        super().__init__(*args,center_blocks=center_blocks,**kwargs)

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


class IllustratedProblemScene(ComparisonScene):
    """Center a concrete illustration beside a separately built data block.

    An illustration is not the first row of a two-column proof. Its complete
    visible group stays centered vertically while the item data grows.
    """
    centered_slots=('left',)
    block_slots=('right',)

    def __init__(self,*args,center_blocks=False,**kwargs):
        # This specialization centers the illustration independently of the
        # data block, rather than sharing a top across comparison columns.
        super().__init__(*args,center_blocks=center_blocks,**kwargs)


class WorkedExampleScene(ComparisonScene):
    """Center problem data and its working independently, without matching rows.

    Each panel reserves its own completed height across the explanation. A
    short calculation must not inherit the top edge of a taller item panel.
    """
    shared_block_height=False


class PairedScene(ComparisonScene):
    """Explanatory steps and their examples share named row envelopes."""
    def __init__(self,*args,pairs,**kwargs):
        self.pairs=tuple(tuple(pair) for pair in pairs)
        # The paired-row algorithm below owns the joint block's centering.
        kwargs.setdefault('center_blocks',False)
        super().__init__(*args,**kwargs)

    def paired_heights(self):
        return {str(index):max((self._height(self.items[name]) for name in pair if name in self.items),default=.52)
                for index,pair in enumerate(self.pairs)}

    def _region(self,slot):
        return getattr(self,'_paired_regions',{}).get(slot) or super()._region(slot)

    def _text_width(self,slot):
        # Wrapping uses the full column capacity, not an earlier short row's
        # fitted width. Validation uses the actual centered column below.
        return super()._slots()[slot].width if slot in ('left','right') else super()._text_width(slot)

    def _arrange(self):
        super()._arrange()
        heights=self.paired_heights()
        fit=next((area['scale'] for area in self._fit_report if area['group']=='body'),1.)
        heights.update({key:height*fit for key,height in getattr(self,'_sequence_paired_heights',{}).items()})
        widths=self.block_widths()
        widths.update(getattr(self,'_sequence_block_widths',{}))
        total_height=sum(heights.values())+.28*max(0,len(heights)-1)
        regions=self._slots()
        # Center the two-column argument as one block; retain a shared top
        # for corresponding rows and a common left edge within each column.
        content_widths={slot:widths.get(f'{type(self).__name__}/{slot}',max(
            (item.target.width for item in self.items.values() if item.slot==slot),default=0.))
            for slot in regions}
        total_width=sum(content_widths.values())+self.gutter
        left=self.layout.body.center[0]-total_width/2
        columns={};self._paired_regions={}
        for slot,region in regions.items():
            width=content_widths[slot]
            area=SlideRegion((left+width/2,self.layout.body.center[1],0),max(width,.01),region.height)
            self._paired_regions[slot]=area
            columns[slot]=ColumnLayout(area,padding=0,gap=.28,content_height=total_height)
            left+=width+self.gutter
        from .core.proof import first_line_of
        from manim import UP
        for index,pair in enumerate(self.pairs):
            for column in columns.values():column.reserve(str(index),heights[str(index)])
            for name in pair:
                if name not in self.items:continue
                item=self.items[name];columns[item.slot].place(str(index),item.target)
                # Align the first readable line rather than the bounding-box
                # center of a multiline example or a fraction.
                top=columns[item.slot]._slots[str(index)][0]
                item.target.shift((0,top-first_line_of(item.target).get_top()[1],0))

    def block_widths(self):
        return {f'{type(self).__name__}/{slot}':max(
            (item.target.width for item in self.items.values() if item.slot==slot),default=0.)
            for slot in self._slots()}

    def _fit_areas(self):
        areas=super()._fit_areas()
        heights=getattr(self,'_sequence_paired_heights',None) or self.paired_heights()
        # The paired row heights, not either independent stack, own capacity.
        height=sum(heights.values());width=max(region.width for region in self._slots().values())
        rows=[item for item in self.items.values() if item.slot in ('left','right')]
        areas.append(FitArea('body',rows,width,self.layout.body.height-.28*(len(heights)-1),minimum_height=height))
        return areas


class SelectionScene(SlotScene):
    """Keep selectable items above their container and accumulating arithmetic."""
    ROWS=(('items',1),('details',1))
    # Cards, the bag gauge and the calculation all contain peer labels.
    # Fit them together; independently shrinking the bag also shrinks only
    # its labels, even when both sets use the same typography role.
    diagram_slots=()
    centered_slots=('items','bag')
    block_slots=('calculation',)

    def _slots(self):
        regions=super()._slots()
        bag,calculation=regions.pop('details').split_columns(1,2,gutter=self.gutter)
        return {**regions,'bag':bag,'calculation':calculation}


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
    block_slots=('equation',)


class TreeExplanationScene(SlotScene):
    ROWS=(('diagram',3.5),('equations',2.5))
    diagram_slots=('diagram',)
    centered_slots=('diagram',)
    block_slots=('equations',)


class TreeArrayScene(SlotScene):
    ROWS=(('diagram',4),('array',1))
    diagram_slots=('diagram','array')
    centered_slots=('diagram','array')
