"""Author nested slides without coordinates or separate rendering machinery."""
from collections import OrderedDict
from dataclasses import replace

from .composition import SlideView
from .panels import Panel, PanelLeaf, RegionPanel, CenterPanel, PanelFitArea, apply_panel_envelopes


class PanelSlide(SlideView):
    """A slide owns panel recipes; the compiler owns flattened leaf placements.

    Use stable paths such as ``proof/step/expression`` to edit content. Paths
    identify positions; shared ``SlideObject`` handles identify moving objects.
    """
    def __init__(self,*args,**kwargs):
        self._author_panels=OrderedDict()
        self._author_regions={}
        super().__init__(*args,**kwargs)

    def fork(self):
        result=super().fork()
        result._author_panels=OrderedDict((name,panel.fork()) for name,panel in self._author_panels.items())
        result._author_regions=self._author_regions.copy()
        return result

    def _insert(self,name,value,slot,**options):
        handle=super()._insert(name,value,slot,**options)
        if getattr(handle.planned_mobject,'_algovis_inherit_panel_theme',False):
            from .semantics import set_semantics
            set_semantics(self.items[name].target,theme=self.theme)
        return handle

    def add_panel(self,name,panel,*,region='body'):
        if not isinstance(panel,Panel):raise TypeError('add_panel needs a Panel')
        if not name or '/' in name or name in self._author_panels:raise ValueError('Panel name must be unique')
        self.layout.region(region)
        template=panel.fork()
        old_panels=self._author_panels.copy();old_regions=self._author_regions.copy()
        try:
            with self._editing():
                self._author_panels[name]=template;self._author_regions[name]=region
                for path,leaf in template.leaves():
                    key='/'.join((name,*path))
                    self._insert(key,leaf.value,'panel:'+name,font_scale=leaf.font_scale,font_reason=leaf.font_reason)
                    leaf.name=key
        except Exception:
            self._author_panels,self._author_regions=old_panels,old_regions
            raise
        return self

    def _bound_author_panels(self):
        return OrderedDict((name,panel.rebind(self.items)) for name,panel in self._author_panels.items())

    def _region(self,slot):
        if slot.startswith('panel:'):
            return self.layout.region(self._author_regions[slot[6:]])
        return super()._region(slot)

    def _panel_recipe(self):
        root=RegionPanel()
        scale=getattr(self,'_sequence_fit_scales',{}).get('body',
            next((row['scale'] for row in self._fit_report if row['group']=='body'),1.))
        for name,panel in self._bound_author_panels().items():
            envelope=getattr(self,'_sequence_panel_envelopes',None)
            if envelope:apply_panel_envelopes(panel,envelope,(name,),scale=scale)
            root.in_region(name,self._region('panel:'+name),panel)
        for name,item in self.items.items():
            if not item.slot.startswith('panel:'):
                root.in_region(name,self._region(item.slot),CenterPanel.bound([(name,item)]))
        return root

    def _fit_areas(self):
        result=[]
        for name,panel in self._bound_author_panels().items():
            envelope=getattr(self,'_sequence_panel_envelopes',None)
            if envelope:apply_panel_envelopes(panel,envelope,(name,))
            result.append(PanelFitArea('body',panel,self._region('panel:'+name)))
        result.extend(area for area in super()._fit_areas() if all(not item.slot.startswith('panel:') for item in area.items))
        return result

    def _position(self,path):
        names=path.split('/');panel=self._author_panels[names[0]]
        for name in names[1:-1]:
            panel=panel.children[name]
            if not isinstance(panel,Panel):raise ValueError('A destination path must name a panel')
        return panel,names[-1]

    def add_at(self,path,value,**options):
        panel,name=self._position(path)
        if name in panel.children:raise ValueError('Position is occupied; use replace_at')
        try:
            with self._editing():
                handle=self._insert(path,value,'panel:'+path.split('/')[0],**options)
                panel.children[name]=PanelLeaf(path,handle)
        except Exception:
            panel.children.pop(name,None)
            raise
        return handle

    def add_panel_at(self,path,panel):
        """Add a nested group as a layout container, preserving child handles."""
        destination,name=self._position(path)
        if name in destination.children:raise ValueError('Panel position is occupied')
        if not isinstance(panel,Panel):raise TypeError('A nested layout must be a Panel')
        template=panel.fork()
        try:
            with self._editing():
                destination.panel(name,template)
                for local,leaf in template.leaves():
                    key='/'.join((path,*local))
                    self._insert(key,leaf.value,'panel:'+path.split('/')[0],
                                 font_scale=leaf.font_scale,font_reason=leaf.font_reason)
                    leaf.name=key
        except Exception:
            destination.children.pop(name,None)
            raise
        return self

    def remove(self,path):
        if '/' not in path:return super().remove(path)
        panel,name=self._position(path);previous=panel.children.copy()
        try:
            with self._editing():
                del panel.children[name];del self.items[path]
                self.definition_uses.pop(path,None)
        except Exception:
            panel.children=previous
            raise
        return self

    def replace_at(self,path,value):
        """A different occupant of one named position replaces it in place."""
        panel,name=self._position(path)
        if not isinstance(panel.children[name],PanelLeaf):raise ValueError('Replace an object position, not a panel')
        old=panel.children[name]
        try:
            with self._editing():
                prior=self.items.pop(path)
                handle=self._insert(path,value,prior.slot,font_scale=prior.font_scale,font_reason=prior.font_reason)
                panel.children[name]=PanelLeaf(path,handle)
        except Exception:
            panel.children[name]=old
            raise
        return self

    def reparent(self,path,to):
        """Move an existing identity to a different named panel position."""
        source,name=self._position(path);destination,new_name=self._position(to)
        if new_name in destination.children:raise ValueError('Destination position is occupied')
        leaf=source.children[name]
        if not isinstance(leaf,PanelLeaf):raise ValueError('Reparent an object position')
        source_children=source.children.copy();destination_children=destination.children.copy()
        try:
            with self._editing():
                del source.children[name]
                destination.children[new_name]=PanelLeaf(to,leaf.value)
                item=self.items.pop(path)
                self.items[to]=replace(item,slot='panel:'+to.split('/')[0])
                if path in self.definition_uses:self.definition_uses[to]=self.definition_uses.pop(path)
        except Exception:
            source.children=source_children;destination.children=destination_children
            raise
        return self
