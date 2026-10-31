"""Semantic scene locations with scene-owned geometry and typography."""
from manim import LEFT, Group
import numpy as np
from .composition import ColumnSlide, SlideView
from .fitting import FitArea
from .layout import ColumnLayout
from .presentation import SlideRegion


class CenteredScene(ColumnSlide):
    """A centered vertical stack, for a title or one compact argument."""
    def _panel_recipe(self):
        from .panels import CenteredColumnPanel
        root=super()._panel_recipe()
        root.children['body']=CenteredColumnPanel.bound(
            [(name,item) for name,item in self.items.items() if item.slot=='body'],
            gap=self.gap,padding=self.padding,vertical='top',center_block=False)
        return root


class BlockScene(ColumnSlide):
    """One compact argument, centered as a block with internally aligned rows."""
    def block_widths(self):
        return {'BlockScene/body':max((item.target.width for item in self.items.values()
                                     if item.slot=='body'),default=0.)}

    def block_heights(self):
        rows=[item for item in self.items.values() if item.slot=='body']
        return {'BlockScene/body':sum(self._height(item) for item in rows)+self.gap*max(0,len(rows)-1)}

    def _panel_recipe(self):
        from .panels import Panel, RegionPanel, CenterPanel
        widths=self.block_widths();widths.update(getattr(self,'_sequence_block_widths',{}))
        heights=self.block_heights();heights.update(getattr(self,'_sequence_block_heights',{}))
        root=RegionPanel()
        panel=Panel.bound([(name,item) for name,item in self.items.items() if item.slot=='body'],gap=self.gap)
        panel.content_width=widths['BlockScene/body'] or None
        panel.content_height=heights['BlockScene/body'] or None
        root.in_region('body',self.layout.body,panel)
        for name,item in self.items.items():
            if item.slot!='body':
                root.in_region(name,self.layout.region(item.slot),CenterPanel.bound([(name,item)]))
        return root


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
    block_slots=None
    shared_block_height=True
    gutter=.35

    def __init__(self,*args,center_blocks=False,context=False,**kwargs):
        self._width_fill=frozenset()
        self.center_blocks=bool(center_blocks)
        if context:
            if self.COLUMNS:raise ValueError('A context row requires a row-based scene')
            self.ROWS=(*self.ROWS,('context',.65))
            if self.block_slots is not None:
                self.block_slots=(*self.block_slots,'context')
        if center_blocks:
            self.block_slots=tuple(key for key,_ in self.COLUMNS)
        elif self.block_slots is None:
            # Text uses a centered common-edge block by default. Diagram
            # specializations retain their explicitly centered geometry.
            self.block_slots=tuple(key for key,_ in (self.COLUMNS or self.ROWS)
                if key not in (*self.diagram_slots,*self.centered_slots))
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

    def definition_route(self,source,destination,*,vacant_destination=False):
        """Keep carried definitions clear of the other semantic rows.

        Footer/context definitions are ordinary sources too. Their route must
        account for explanatory rows between the source and the equation.
        """
        from .composition import _definition_route
        return _definition_route(self,source,destination,
            [item for item in self.items.values() if item.slot!='header'],vacant_destination=vacant_destination)

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

    def _panel_recipe(self):
        from .panels import Panel, CenterPanel, CenteredColumnPanel, RegionPanel
        root=RegionPanel()
        widths=self.block_widths()
        widths.update(getattr(self,'_sequence_block_widths',{}))
        heights=self.block_heights()
        heights.update(getattr(self,'_sequence_block_heights',{}))
        for slot,region in self._slots().items():
            items=[(name,item) for name,item in self.items.items() if item.slot==slot]
            width=widths.get(f'{type(self).__name__}/{slot}')
            height=heights.get(f'{type(self).__name__}/{slot}')
            cls=CenteredColumnPanel if slot in self.centered_slots else Panel
            panel=cls.bound(items,gap=.28,vertical='center' if height else 'top',center_block=bool(width))
            panel.content_width=width or None
            panel.content_height=height or None
            root.in_region(slot,region,panel)
        footer=[(name,item) for name,item in self.items.items() if item.slot=='footer']
        if len(footer)>1:
            from .panels import FooterPanel
            root.in_region('footer',self.layout.footer,FooterPanel.bound(footer,gap=.1,vertical='top'))
        for name,item in self.items.items():
            if item.slot not in self._slots() and not (item.slot=='footer' and len(footer)>1):
                root.in_region(name,self.layout.region(item.slot),CenterPanel.bound([(name,item)]))
        return root


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


class ArgumentScene(SlotScene):
    """Named stages of one growing, centered, left-aligned argument.

    Semantic locations remain exposed, but their empty proportional bands do
    not scatter a short explanation across the frame. The sequence reserves
    the complete argument's envelope before the first line appears.
    """
    argument_copy_corridor=True
    def motion_gap(self):
        """Reserve a readable landing band for a routed definition copy."""
        heights=[]
        for use in self.definition_uses.values():
            mob=use.source.mobject
            fit=getattr(mob,'_algovis_view_fit_scale',1.)
            heights.append(mob.height/fit+.32)
        for item in self.items.values():
            for source in getattr(item.target,'_copy_sources',{}).values():
                mob=source.mobject
                # A retained source can also need the band: the copy may
                # approach below an existing prefix, just above the next
                # explanation row. Retiring sources need the same clearance.
                fit=getattr(mob,'_algovis_view_fit_scale',1.)
                heights.append(mob.height/fit+.32)
        return max([.34,*heights])

    def _argument_gap(self):
        return max(self.motion_gap(),getattr(self,'_sequence_motion_gap',.34))

    def motion_reservation(self):
        """Reserve side corridors when a definition must cross another row."""
        slots=[key for key,_ in self.ROWS]+['footer']
        widths=[]
        for name,use in self.definition_uses.items():
            destination=self.items[name]
            source_ink={id(p) for p in use.source.mobject.get_family()}
            owner=next((item for item in self.items.values()
                if source_ink<={id(p) for p in item.object.mobject.get_family()}),None)
            if owner is None or owner.slot not in slots or destination.slot not in slots:continue
            a,b=sorted((slots.index(owner.slot),slots.index(destination.slot)))
            if not any(item.slot in slots[a+1:b] for item in self.items.values()):continue
            target=destination.target
            for key in use.part.split('.'):target=target.part(key)
            source=use.source.mobject
            fit=getattr(source,'_algovis_view_fit_scale',1.)
            widths.append(max(source.width/fit,target.width)+.16)
        return max(widths,default=0.)

    def _argument_region(self):
        body=self.layout.body
        margin=max(self.motion_reservation(),getattr(self,'_sequence_motion_margin',0.))
        if 2*margin>=body.width:
            raise ValueError('A definition transfer needs more room; use an adjacent application layout')
        return SlideRegion(body.center,body.width-2*margin,body.height)

    def _slots(self):
        # These names are stages in one argument, not disjoint rectangles.
        return {slot:self._argument_region() for slot,_ in self.ROWS}

    def _argument_items(self):
        return [(name,item) for slot,_ in self.ROWS for name,item in self.items.items() if item.slot==slot]

    def block_widths(self):
        return {'ArgumentScene/body':max((i.target.width for _,i in self._argument_items()),default=0.)}

    def block_heights(self):
        rows=self._argument_items()
        return {'ArgumentScene/body':sum(self._height(i) for _,i in rows)+self._argument_gap()*max(0,len(rows)-1)}

    def _fit_areas(self):
        rows=[item for _,item in self._argument_items()]
        region=self._argument_region()
        areas=[FitArea('body',rows,region.width,region.height,stacked=True,gap=self._argument_gap())]
        for area in super()._fit_areas():
            if area.group=='header':areas.append(area)
            elif area.group=='footer':
                # A retained reference definition is a peer of the argument,
                # even when it lives in the footer for a later application.
                # Its region constrains the shared fit; it must not acquire an
                # independent, larger equation size as the argument grows.
                area.group='body'
                areas.append(area)
        return areas

    def _panel_recipe(self):
        from .panels import Panel
        root=super()._panel_recipe()
        for slot,_ in self.ROWS:
            root.children.pop(slot,None);root.regions.pop(slot,None)
        widths={**self.block_widths(),**getattr(self,'_sequence_block_widths',{})}
        heights={**self.block_heights(),**getattr(self,'_sequence_block_heights',{})}
        panel=Panel.bound(self._argument_items(),gap=self._argument_gap())
        panel.content_width=widths['ArgumentScene/body'] or None
        panel.content_height=heights['ArgumentScene/body'] or None
        root.in_region('argument',self._argument_region(),panel)
        return root


class DerivationScene(ArgumentScene):
    ROWS=(('meaning',1),('equation',2),('explanation',1))
    block_slots=('meaning','equation','explanation')


class RecurrenceScene(ArgumentScene):
    """Keep the function meaning, recurrence and base case visible together."""
    ROWS=(('meaning',1),('equation',2),('base',1.6),('explanation',.8))
    block_slots=('meaning','equation','base','explanation')


class ApplicationScene(ArgumentScene):
    """Read an answer from a completed rule and its English meaning.

    The reference rule precedes the conditions. The general meaning and its
    instantiated copy are neighbors, so a full prose definition does not have
    to travel through the retained algorithm's ink.
    """
    ROWS=(('reference',2),('conditions',1),('definition',1),('application',1))


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
        return getattr(self,'_allocated_panel_regions',{}).get(slot) or super()._region(slot)

    def _text_width(self,slot):
        # Wrapping uses the full column capacity, not an earlier short row's
        # fitted width. Validation uses the actual centered column below.
        return super()._slots()[slot].width if slot in ('left','right') else super()._text_width(slot)

    def _panel_recipe(self):
        from .panels import PairedPanel
        root=super()._panel_recipe()
        heights=self.paired_heights()
        fit=next((area['scale'] for area in self._fit_report if area['group']=='body'),1.)
        heights.update({key:height*fit for key,height in getattr(self,'_sequence_paired_heights',{}).items()})
        widths={**self.block_widths(),**getattr(self,'_sequence_block_widths',{})}
        content_widths={slot:widths.get(f'{type(self).__name__}/{slot}',0.) for slot in self._slots()}
        pair=PairedPanel(pairs=self.pairs,heights=heights,widths=content_widths,gap=self.gutter)
        for slot in self._slots():
            pair.panel(slot,root.children.pop(slot));root.regions.pop(slot)
        root.in_region('paired',self.layout.body,pair)
        return root

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

    def _panel_recipe(self):
        from .panels import ConversionPanel
        root=super()._panel_recipe()
        conversion=ConversionPanel(self._slots())
        for slot in self._slots():
            conversion.panel(slot,root.children.pop(slot));root.regions.pop(slot)
        root.in_region('conversion',self.layout.body,conversion)
        return root


class AnalysisScene(SlotScene):
    """A centered definition, paired derivations and aligned result row."""
    ROWS=(('definition',1.7),('comparison',3.5),('results',.7))
    block_slots=('definition','left','right','left_result','right_result')

    def __init__(self,*args,summary=False,**kwargs):
        if summary:
            self.ROWS=(*self.ROWS,('summary',.65))
            self.block_slots=(*self.block_slots,'summary')
        super().__init__(*args,**kwargs)

    def block_heights(self):
        heights=super().block_heights()
        prefix=type(self).__name__
        for pair in (('left','right'),('left_result','right_result')):
            maximum=max(heights[f'{prefix}/{slot}'] for slot in pair)
            for slot in pair:heights[f'{prefix}/{slot}']=maximum
        return heights

    def _region(self,slot):
        return getattr(self,'_allocated_panel_regions',{}).get(slot) or super()._region(slot)

    def _text_width(self,slot):
        return self._slots()[slot].width if slot in self._slots() else super()._text_width(slot)

    def _panel_recipe(self):
        from .panels import AnalysisPanel
        root=super()._panel_recipe()
        widths={**self.block_widths(),**getattr(self,'_sequence_block_widths',{})}
        sides={side:max(widths.get(f'{type(self).__name__}/{slot}',0.) for slot in (side,side+'_result'))
               for side in ('left','right')}
        analysis=AnalysisPanel(sides,gap=self.gutter)
        for side in ('left','right'):
            for slot in (side,side+'_result'):
                analysis.in_region(slot,root.regions.pop(slot),root.children.pop(slot))
        root.in_region('analysis',self.layout.body,analysis)
        return root

    def _slots(self):
        regions=super()._slots()
        left,right=regions.pop('comparison').split_columns(1,1,gutter=self.gutter)
        a,b=regions.pop('results').split_columns(1,1,gutter=self.gutter)
        return {**regions,'left':left,'right':right,'left_result':a,'right_result':b}


class RecapScene(SlotScene):
    """Keep a numbered method beside its consequences, with room for a brace."""
    COLUMNS=(('steps',7.5),('consequences',5.5))
    shared_block_height=False

    def __init__(self,*args,center_blocks=True,**kwargs):
        super().__init__(*args,center_blocks=center_blocks,**kwargs)


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
