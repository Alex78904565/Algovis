"""Detached slide layouts and transitions based on object identity.

A Manim Scene owns the clock. These small view classes describe what is on the
board at a particular point in that clock. Planning a future view never moves
the live artwork.
"""
from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from copy import copy
from dataclasses import dataclass, replace
import warnings
from itertools import count

import numpy as np
from manim import AnimationGroup, FadeIn, FadeOut, Group, Mobject, Succession, Text, Transform, VGroup, Wait, config

from .core.math import ApplyDefinition
from .core.math_row import MathRow
from .core.proof import first_line_of
from .frames import EquationFrame, ProofFrame
from .layout import ColumnLayout, LessonTypography, assign_scene_typography
from .fitting import FitArea, FitPolicy, plain_text, relative_font_scale
from .semantics import copy_semantics, set_semantics
from .theme import DEFAULT_THEME
from .utils.effects import DeferredAnimation


class SlideObject:
    """A live object that can be shared between independently planned views.

    ``copy()`` makes a new object at this object's position and remembers its
    source. The transition carries that copy to the new view's planned position.
    Ordinary Manim ``mobject.copy()`` remains a plain, unrelated copy.
    """

    def __init__(self, mobject, *, copied_from=None):
        if not isinstance(mobject, Mobject):
            raise TypeError("A SlideObject wraps a Manim mobject")
        self.mobject = mobject
        self.copied_from = copied_from

    def copy(self):
        return SlideObject(self.planned_mobject.copy(), copied_from=self)

    @property
    def planned_mobject(self):
        """The latest authored content, independent of the live render clock."""
        return self._planned_model if '_planned_model' in self.__dict__ else self.mobject

    @property
    def tex(self):return self.planned_mobject.tex_string

    def __deepcopy__(self,memo):
        # A logical reference in an equation or layout keeps its live identity.
        # Explicit copy() is the operation that creates a new visual identity.
        memo[id(self)]=self
        return self


    def part(self, name):
        """Select a stable named mathematical term as a copy source."""
        if '_planned_model' in self.__dict__:
            part=self.planned_mobject
            for key in name.split('.'):part=part.part(key)
            return PlannedPart(self,name,part.tex_string,
                meaning=getattr(part,'semantics',None),theme=getattr(part,'_semantic_theme',None))
        if not hasattr(type(self.mobject),'part'):
            raise TypeError("Named terms require a component with named parts")
        part=self.mobject
        for key in name.split('.'):
            part=part.part(key)
        part._view_attention_term = True
        return SlideObject(part)

    def on_word(self, cue, *, style='auto', reason, duration=.45, callback=None):
        """Declare attention once; ViewSceneMixin schedules its spoken trigger."""
        from .attention import attention_declaration
        anchor=self.owner.mobject if isinstance(self,PlannedPart) else self.mobject
        if isinstance(self,PlannedPart) and style=='auto':style='box'
        binding = attention_declaration(self, cue, style=style, reason=reason,
                                        duration=duration, callback=callback)
        declarations = list(getattr(anchor, '_view_word_attention', ()))
        declarations.append(binding)
        anchor._view_word_attention = declarations
        anchor._view_attention_owner = id(anchor)
        return self


class PlannedPart(SlideObject):
    """A term's planned content now, and its actual source artwork at playback."""
    def __init__(self,owner,path,tex,*,meaning=None,theme=None):
        self.owner,self.path,self._tex=owner,path,tex
        self.copied_from=None
        if meaning is not None:self.semantics=meaning
        if theme is not None:self._semantic_theme=theme

    @property
    def tex(self):return self._tex

    @property
    def mobject(self):
        result=self.owner.mobject
        for key in self.path.split('.'):result=result.part(key)
        return result


@dataclass
class Placement:
    object: SlideObject
    target: Mobject
    slot: str
    via: tuple = ()
    path_arc: float = 0
    ascent: float | None = None
    descent: float | None = None
    baseline_offset: float | None = None
    offset: tuple = (0., 0., 0.)
    offset_reason: str = ''
    fit_scale: float = 1.
    font_scale: float = 1.
    font_reason: str = ''


class LayoutOverrideWarning(UserWarning):
    """A deliberate departure from a shared layout's automatic alignment."""


@dataclass(frozen=True)
class DefinitionUse:
    source: SlideObject
    part: str
    via: tuple = ()
    path_arc: float = 0


def _object(value):
    return value if isinstance(value, SlideObject) else SlideObject(value)


def _same_picture(first, second):
    """Skip identical artwork, including its paint, rather than animating it."""
    a, b = first.get_family(), second.get_family()
    if len(a) != len(b):
        return False
    attributes = ("points", "fill_rgbas", "stroke_rgbas", "stroke_width",
                  "background_stroke_rgbas", "background_stroke_width",
                  "z_index", "pixel_array")
    for left, right in zip(a, b):
        if type(left) is not type(right):
            return False
        for attribute in attributes:
            x, y = getattr(left, attribute, None), getattr(right, attribute, None)
            if x is y:continue
            if x is None or y is None:
                if x is not y:
                    return False
                continue
            x, y = np.asarray(x), np.asarray(y)
            if x.shape != y.shape or not np.allclose(x, y, atol=1e-9, rtol=0):
                return False
    return True


def _content_model(mob):
    """Content and semantic component options, independent of layout/paint."""
    fields=('slot_tex','tex_string','text','profile','reveal_depth','columns',
            'weight_visible','value_visible','capacity','current_val')
    values=tuple((field,repr(getattr(mob,field))) for field in fields if field in mob.__dict__)
    return (type(mob),values,tuple(_content_model(child) for child in mob.submobjects))


def _semantic_edits(before,after,path=()):
    if getattr(before,'semantics',None)!=getattr(after,'semantics',None):
        if hasattr(after,'semantics'):yield path,after
    for index,(old,new) in enumerate(zip(before.submobjects,after.submobjects)):
        yield from _semantic_edits(old,new,(*path,index))


class SlideView:
    """A final composition built from detached targets and stable live objects."""

    _type_groups = count(1)

    def __init__(self, title=None, *, theme=DEFAULT_THEME, layout=None, auto_fit=True,
                 typography=None):
        from .presentation import Slide, SlideLayout
        self.theme = theme
        self.typography = typography or LessonTypography()
        self._type_group = f'{type(self).__name__}/{next(self._type_groups)}'
        self.layout = layout or SlideLayout()
        self.fit_policy = auto_fit if isinstance(auto_fit,FitPolicy) else FitPolicy(enabled=bool(auto_fit))
        self._fit_report = []
        self.items = OrderedDict()
        self.definition_uses = {}
        self._default_centers = {}
        self._warned_offsets = set()
        if title is not None:
            heading = (Slide(title, theme=theme, layout=self.layout).header
                       if isinstance(title, str) else title)
            self._insert("title", heading, "header")
            self._fit_and_arrange()
            self._remember_defaults()

    def fork(self):
        """Copy the layout, retaining the identities of all its live objects."""
        view = copy(self)
        if hasattr(self,'frame'):
            view.frame=copy(self.frame)
            view.frame.rows=self.frame.rows.copy()
        view.items = OrderedDict((name, replace(item, target=item.target.copy()))
                                 for name, item in self.items.items())
        # A previous substitution explains that transition only.
        view.definition_uses = {}
        view._default_centers = {name: point.copy() for name, point in self._default_centers.items()}
        view._warned_offsets = set(self._warned_offsets)
        view._fit_report = [dict(item) for item in self._fit_report]
        return view

    def object(self, name):
        return self.items[name].object

    def snapshot(self):
        """Freeze this exact beat, including its definition-transfer intent.

        fork() starts a new authored state and clears a preceding transition's
        one-shot copies. The timeline must preserve those copies when storing
        and compiling the state that actually applies them.
        """
        view=self.fork()
        view.definition_uses=self.definition_uses.copy()
        return view

    def target(self, name):
        """The detached final artwork, useful for inspecting or styling a view."""
        return self.items[name].target

    def _remember_model(self,name):
        # Only explicit authoring edits update this content snapshot. Fitting,
        # forks and compiler snapshots must not overwrite it while measuring
        # an earlier beat. No live geometry is touched.
        item=self.items[name]
        item.object._planned_model=item.target.copy()
        item.object._planned_model._algovis_font_scale_reason=item.font_reason
        relative_font_scale(item.object._planned_model,item.font_scale)

    def copy(self,name):
        """Copy this planned state, even when its earlier beat has not played."""
        return SlideObject(self.target(name).copy(),copied_from=self.object(name))

    def part(self,name,path):
        """Borrow a named term from this scene's planned object state."""
        target=self.target(name)
        for key in path.split('.'):target=target.part(key)
        return PlannedPart(self.object(name),path,target.tex_string,
                           meaning=getattr(target,'semantics',None),
                           theme=getattr(target,'_semantic_theme',None))

    def retain_live_models(self,previous):
        """Carry intrinsic process results into unchanged planned components.

        Scene layout still owns their new positions. Explicit content edits
        remain authoritative; explicit semantic edits apply over the live state.
        This keeps an early-planned next scene from undoing a population/reveal.
        """
        prior={id(item.object.mobject):item for item in previous.items.values()}
        with self._editing():
            for name,item in self.items.items():
                old=prior.get(id(item.object.mobject))
                if old is None or _content_model(old.target)!=_content_model(item.target):continue
                live=item.object.mobject.copy()
                factor=getattr(live,'_algovis_view_fit_scale',1.)
                if factor!=1:live.scale(1/factor)
                live._algovis_view_fit_scale=1.
                for path,meaning in _semantic_edits(old.target,item.target):
                    node=live
                    for index in path:node=node.submobjects[index]
                    copy_semantics(meaning,node);set_semantics(node)
                if hasattr(item.target,'_copy_sources'):live._copy_sources=item.target._copy_sources.copy()
                role='heading' if item.slot=='header' else 'proof_label' if item.slot.startswith('label:') else None
                assign_scene_typography(live,self.typography,group=self._type_group,role=role)
                inherited=getattr(live,'_algovis_relative_font_scale',1.)
                live.scale(item.font_scale/inherited)
                self.items[name]=replace(item,target=live,fit_scale=1.)
        return self

    def _insert(self, name, value, slot, *, via=(), path_arc=0, font_scale=None,
                font_reason=None):
        if name in self.items:
            raise ValueError(f"Duplicate slide item: {name!r}; use move or substitute")
        if isinstance(value,str):
            value = plain_text(value,self._text_width(slot),theme=self.theme,
                               wrap=self.fit_policy.enabled and self.fit_policy.wrap_text,
                               typography=self.typography)
        handle = _object(value)
        target = handle.planned_mobject.copy()
        prior_fit = getattr(target,'_algovis_view_fit_scale',1.)
        if prior_fit != 1:
            target.scale(1/prior_fit)
        target._algovis_view_fit_scale = 1.
        inherited=getattr(target,'_algovis_relative_font_scale',1.)
        factor=inherited if font_scale is None else float(font_scale)
        reason = font_reason or getattr(target,'_algovis_font_scale_reason','')
        if factor != 1 and not str(reason).strip():
            raise ValueError('A relative font override needs font_reason explaining its hierarchy')
        role = ('heading' if slot == 'header' else 'proof_label' if slot.startswith('label:')
                else 'note' if slot == 'footer' else None)
        assign_scene_typography(target,self.typography,group=self._type_group,role=role)
        relative_font_scale(target,factor)
        target.scale(factor/inherited)
        target._algovis_font_scale_reason=str(reason)
        metrics = {}
        if isinstance(target, MathRow):
            metrics = dict(ascent=float(target.get_top()[1]-target.baseline),
                           descent=float(target.baseline-target.get_bottom()[1]),
                           baseline_offset=float(target.baseline-target.get_y()))
        self.items[name] = Placement(handle, target, slot, tuple(via), path_arc,
                                     font_scale=factor,font_reason=str(reason), **metrics)
        return handle

    @contextmanager
    def _editing(self):
        # Layout failure must not leave a partly rearranged future slide.
        previous, previous_uses = self.items, self.definition_uses
        previous_defaults, previous_warnings = self._default_centers, set(self._warned_offsets)
        previous_fit = self._fit_report
        previous_frame_rows=self.frame.rows.copy() if hasattr(self,'frame') else None
        previous_proof_regions=getattr(self,'_proof_regions',{}).copy()
        self.items = OrderedDict((name, replace(item, target=item.target.copy()))
                                 for name, item in previous.items())
        self.definition_uses = dict(previous_uses)
        try:
            for item in self.items.values():
                if item.fit_scale != 1:
                    self._scale_item(item,1/item.fit_scale)
                    item.fit_scale = 1.
            yield
            self._fit_and_arrange()
            self._remember_defaults()
            for item in self.items.values():
                item.target.shift(item.offset)
            self.validate()
        except Exception:
            self.items, self.definition_uses = previous, previous_uses
            self._default_centers, self._warned_offsets = previous_defaults, previous_warnings
            self._fit_report = previous_fit
            if previous_frame_rows is not None:self.frame.rows=previous_frame_rows
            if hasattr(self,'_proof_regions'):self._proof_regions=previous_proof_regions
            raise

    def add(self, name, value, *, region="body", via=(), path_arc=0, font_scale=None,
            font_reason=None):
        """Place an object in a named safe region without touching the live one."""
        with self._editing():
            handle = self._insert(name, value, region, via=via, path_arc=path_arc,
                                  font_scale=font_scale,font_reason=font_reason)
        return handle

    def set_font_scale(self, name, factor, *, reason):
        """Change a text size relative to its natural role, without coordinates."""
        factor=float(factor)
        if not str(reason).strip():
            raise ValueError('A relative font override needs a hierarchy reason')
        with self._editing():
            item=self.items[name]
            relative_font_scale(item.target,factor)
            self._scale_item(item,factor/item.font_scale)
            item.font_scale=factor
            item.font_reason=str(reason)
            item.target._algovis_font_scale_reason=str(reason)
        return self

    def move(self, name, *, region, via=(), path_arc=0):
        with self._editing():
            item = self.items[name]
            self.items[name] = replace(item, slot=region, via=tuple(via), path_arc=path_arc,
                                       offset=(0., 0., 0.), offset_reason='')
        return self

    def offset(self, name, vector, *, reason):
        """Explicitly depart from a shared anchor, with a reviewable explanation."""
        vector = np.asarray(vector, dtype=float)
        if vector.shape != (3,) or not np.isfinite(vector).all() or not str(reason).strip():
            raise ValueError('An offset needs a finite 3D vector and an alignment reason')
        with self._editing():
            self.items[name] = replace(self.items[name], offset=tuple(vector), offset_reason=str(reason))
        return self

    def _remember_defaults(self):
        self._default_centers = {name: item.target.get_center().copy() for name, item in self.items.items()}

    def layout_report(self):
        overrides = []
        for name, item in self.items.items():
            default = self._default_centers.get(name)
            if default is None: continue
            delta = item.target.get_center()-default
            if np.linalg.norm(delta) > .0035:
                overrides.append({'object':name, 'offset':delta.tolist(),
                                  'reason':item.offset_reason or 'Unexplained direct target adjustment'})
        return {'layout':type(self).__name__, 'overrides':overrides,
                'autoFit':self.fit_policy.enabled,'fitting':[dict(item) for item in self._fit_report],
                'fontScales':{name:item.font_scale for name,item in self.items.items() if item.font_scale!=1},
                'fontReasons':{name:item.font_reason for name,item in self.items.items() if item.font_scale!=1},
                'sceneTypography':{name:self.typography.size(name) for name in self.typography.__dataclass_fields__},
                'layoutGroup':getattr(self,'_sequence_layout_name',None),
                'sharedFit':getattr(self,'_sequence_fit_scales',{}),
                'reviewAlignment':bool(overrides), 'manyOverrides':len(overrides)>=3}

    @staticmethod
    def _scale_item(item, factor):
        item.target.scale(factor)
        for name in ('ascent','descent','baseline_offset'):
            value=getattr(item,name)
            if value is not None:setattr(item,name,value*factor)

    @staticmethod
    def _height(item):
        if isinstance(item.target,MathRow):
            item.ascent=max(item.ascent,float(item.target.get_top()[1]-item.target.baseline))
            item.descent=max(item.descent,float(item.target.baseline-item.target.get_bottom()[1]))
            return item.ascent+item.descent
        return item.target.height

    def _text_width(self, slot):
        return self._region(slot).width

    def _fit_areas(self):
        return [FitArea('body' if item.slot not in ('header','footer') else item.slot,
                        [item],self._region(item.slot).width,self._region(item.slot).height)
                for item in self.items.values() if item.slot != 'chrome']

    def _fit_and_arrange(self):
        self._fit_report=[]
        if self.fit_policy.enabled:
            if self.fit_policy.wrap_text:
                for item in self.items.values():
                    source=getattr(item.target,'_algovis_source_text',None)
                    if source is not None:
                        role=getattr(item.target,'_algovis_type_role','body')
                        wrapped=plain_text(source,self._text_width(item.slot)/item.font_scale,
                                           theme=self.theme,typography=self.typography,type_role=role)
                        copy_semantics(item.target,wrapped)
                        if hasattr(wrapped,'semantics'):set_semantics(wrapped)
                        else:wrapped.set_color(item.target.get_color())
                        wrapped._algovis_font_scale_reason=item.font_reason
                        relative_font_scale(wrapped,item.font_scale)
                        wrapped.scale(item.font_scale)
                        assign_scene_typography(wrapped,self.typography,group=self._type_group,role=role)
                        item.target=wrapped
            for item in self.items.values():relative_font_scale(item.target,item.font_scale)
            areas=self._fit_areas();scales={}
            for area in areas:
                scales[area.group]=min(scales.get(area.group,1.),area.scale(self._height))
            for group,factor in getattr(self,'_sequence_fit_scales',{}).items():
                if group not in scales:continue
                if scales[group]<factor-1e-6:
                    raise ValueError('Content exceeds its planned animation-group envelope; replan the complete group')
                scales[group]=factor
            fitted=set()
            for area in areas:
                factor=scales[area.group]
                self.fit_policy.check(area.items,factor)
                for item in area.items:
                    if id(item) in fitted:continue
                    fitted.add(id(item))
                    self._scale_item(item,factor)
                    item.fit_scale=factor
                    item.target._algovis_view_fit_scale=factor
                self._fit_report.append({'group':area.group,'scale':factor})
        self._arrange()

    def remove(self, name):
        with self._editing():
            del self.items[name]
            self.definition_uses.pop(name, None)
        return self

    def substitute(self, name, *, from_definition=None, via=(), path_arc=0, **parts):
        """Refine one native equation; optionally carry a definition to its term."""
        item = self.items[name]
        if not isinstance(item.target, MathRow):
            raise TypeError("A substitution requires a MathRow")
        if not parts or not set(parts) <= set(item.target.parts):
            raise ValueError("Specify existing named terms to substitute")
        if from_definition is not None and len(parts) != 1:
            raise ValueError("Apply one definition to one named term per transition")
        with self._editing():
            item = self.items[name]
            self.items[name] = replace(item, target=item.target.next_layout(**parts))
            if from_definition is not None:
                self.definition_uses[name] = DefinitionUse(
                    _object(from_definition), next(iter(parts)), tuple(via), path_arc)
            else:
                self.definition_uses.pop(name, None)
        self._remember_model(name)
        return self

    def refine(self,name,**state):
        """Plan a component's next semantic state without changing live artwork."""
        with self._editing():
            item=self.items[name]
            if not hasattr(type(item.target),'with_state'):
                raise TypeError('This component does not expose a semantic state model')
            self.items[name]=replace(item,target=item.target.with_state(**state))
        self._remember_model(name)
        return self

    def apply_definition(self,name,path,source,tex):
        """Carry a definition into a named term inside a case equation."""
        item=self.items[name]
        if not hasattr(type(item.target),'with_state') or not path.startswith('row:'):
            raise TypeError('Nested definition application requires a named case row')
        row_name,term=path.split('.',1)
        index=int(row_name.split(':')[1])
        rows=[row.copy() for row in item.target.rows]
        rows[index]=rows[index].next_layout(**{term:tex})
        self.refine(name,rows=rows)
        self.definition_uses[name]=DefinitionUse(_object(source),path)
        return self

    def revise(self,name,parts,*,meanings=None):
        """Add/remove named terms while preserving every unchanged term owner."""
        with self._editing():
            item=self.items[name]
            if not isinstance(item.target,MathRow):raise TypeError('Revising named terms requires an equation')
            sources={key:value for key,value in parts.items() if isinstance(value,SlideObject)}
            values={key:(value.tex if key in sources else value) for key,value in parts.items()}
            target=item.target.next_layout(values)
            target._copy_sources=sources
            for key,source in sources.items():
                copy_semantics(source if isinstance(source,PlannedPart) else source.mobject,target.part(key))
                if hasattr(target.part(key),'semantics'):set_semantics(target.part(key))
            for key,properties in (meanings or {}).items():
                set_semantics(target.part(key),properties,theme=self.theme)
            self.items[name]=replace(item,target=target)
        self._remember_model(name)
        return self

    def set_meaning(self,name,*,part=None,**properties):
        with self._editing():
            target=self.items[name].target
            if part is not None:target=target.part(part)
            set_semantics(target,theme=self.theme,**properties)
        self._remember_model(name)
        return self

    def reword(self,name,content):
        """Edit prose in place, preserving its role, identity and scene defaults."""
        with self._editing():
            item=self.items[name]
            if not isinstance(item.target,Text):raise TypeError('Rewording requires a text object')
            item.target._algovis_source_text=str(content)
        self._remember_model(name)
        return self

    def _arrange(self):
        for item in self.items.values():
            region = self.layout.region(item.slot)
            item.target.move_to(region.center)

    def validate(self):
        for override in self.layout_report()['overrides']:
            key = (override['object'], tuple(round(value, 4) for value in override['offset']))
            if key not in self._warned_offsets:
                warnings.warn(f"{type(self).__name__}/{override['object']} overrides its shared alignment: "
                              f"{override['reason']}. Review the layout before adding more offsets.",
                              LayoutOverrideWarning, stacklevel=3)
                self._warned_offsets.add(key)
        owners = set()
        for name, item in self.items.items():
            family = {id(obj) for obj in item.object.mobject.get_family()}
            if owners & family:
                raise ValueError("A slide cannot own both a group and its child, or the same object twice")
            owners.update(family)
            region = self._region(item.slot)
            target = item.target
            center = np.array(region.center)
            if (target.get_left()[0] < center[0]-region.width/2-1e-7
                    or target.get_right()[0] > center[0]+region.width/2+1e-7
                    or target.get_bottom()[1] < center[1]-region.height/2-1e-7
                    or target.get_top()[1] > center[1]+region.height/2+1e-7):
                raise ValueError(f"Slide item {name!r} exceeds its region; revise the layout")
        # Overlap inside a composed object (e.g. a tree's nodes and edges) is
        # its own concern. Separate logical items must have separate space.
        items = [(name, item.target) for name, item in self.items.items() if item.slot != "chrome"]
        for index, (name, first) in enumerate(items):
            for other, second in items[index+1:]:
                width = min(first.get_right()[0], second.get_right()[0])-max(first.get_left()[0], second.get_left()[0])
                height = min(first.get_top()[1], second.get_top()[1])-max(first.get_bottom()[1], second.get_bottom()[1])
                if width > .01 and height > .01:
                    raise ValueError(f"Slide items {name!r} and {other!r} overlap; compose them as one object if intentional")
        return self

    def _region(self, slot):
        return self.layout.region(slot)

    def preview(self):
        """Independent final-state art for a still render or layout inspection."""
        self.validate()
        return Group(*(item.target.copy() for item in self.items.values()))

    def transition_to(self, incoming):
        return ViewTransition(self, incoming)

    def install(self, scene):
        """Install final artwork without animation, preserving external objects."""
        self.validate()
        for item in self.items.values():
            _adopt(item.object.mobject, item.target)
        scene.add(*(item.object.mobject for item in self.items.values()))


class ColumnSlide(SlideView):
    """A header and one left-aligned content column, using the shared layout."""

    def __init__(self, title=None, *, gap=.38, padding=.35, **kwargs):
        self.gap, self.padding = gap, padding
        super().__init__(title, **kwargs)

    def _arrange(self):
        column = ColumnLayout(self.layout.body, padding=self.padding, gap=self.gap)
        for name, item in self.items.items():
            if item.slot == "body":
                _column_row(column, name, item)
            else:
                item.target.move_to(self.layout.region(item.slot).center)

    def _text_width(self,slot):
        return super()._text_width(slot)-2*self.padding if slot=='body' else super()._text_width(slot)

    def _fit_areas(self):
        body=[item for item in self.items.values() if item.slot=='body']
        return [FitArea('body',body,self.layout.body.width-2*self.padding,
                        self.layout.body.height-2*self.padding,True,self.gap),
                *(area for area in super()._fit_areas() if area.group!='body')]


class SplitSlide(ColumnSlide):
    """Two nested content columns sharing a header and typography."""

    def __init__(self, title=None, *, weights=(1, 1), gutter=.6, **kwargs):
        self.weights, self.gutter = weights, gutter
        super().__init__(title, **kwargs)

    def add(self, name, value, *, column="left", **options):
        if column not in ("left", "right"):
            raise ValueError("A split-slide column is left or right")
        return SlideView.add(self, name, value, region=column, **options)

    def _region(self, slot):
        if slot in ("left", "right"):
            regions = self.layout.body.split_columns(*self.weights, gutter=self.gutter)
            return regions[0 if slot == "left" else 1]
        return self.layout.region(slot)

    def _arrange(self):
        columns = {name: ColumnLayout(self._region(name), padding=self.padding, gap=self.gap)
                   for name in ("left", "right")}
        for name, item in self.items.items():
            if item.slot in columns:
                _column_row(columns[item.slot], name, item)
            else:
                item.target.move_to(self.layout.region(item.slot).center)

    def _text_width(self,slot):
        return self._region(slot).width-2*self.padding if slot in ('left','right') else self._region(slot).width

    def _fit_areas(self):
        return [*(FitArea('body',[item for item in self.items.values() if item.slot==slot],
            self._region(slot).width-2*self.padding,self._region(slot).height-2*self.padding,True,self.gap)
            for slot in ('left','right')),
            *(FitArea(item.slot,[item],self._region(item.slot).width,self._region(item.slot).height)
              for item in self.items.values() if item.slot in ('header','footer'))]


class EquationSlide(SlideView):
    """Named definition/recurrence/base rows from the shared equation frame."""

    def __init__(self, title=None, *, profile="stacked", **kwargs):
        self.frame = EquationFrame(profile, theme=kwargs.get("theme", DEFAULT_THEME))
        super().__init__(title, **kwargs)

    def add(self, row, value, *, via=(), path_arc=0, font_scale=None,font_reason=None):
        if row not in self.frame.rows:
            raise ValueError(f"Unknown equation row: {row!r}")
        return super().add(row, value, region=row, via=via, path_arc=path_arc,
                           font_scale=font_scale,font_reason=font_reason)

    def _region(self, slot):
        return self.layout.body if slot in self.frame.rows else super()._region(slot)

    def _arrange(self):
        for item in self.items.values():
            if item.slot in self.frame.rows:
                _frame_row(self.frame, item)
            else:
                item.target.move_to(self.layout.region(item.slot).center)

    def _text_width(self,slot):
        if slot in self.frame.rows:
            return min(self.frame.style.equation_right,self.layout.body.center[0]+self.layout.body.width/2)-self.frame.left[0]
        return super()._text_width(slot)

    def _fit_areas(self):
        return _frame_fit_areas(self,self.frame.rows,self.frame.left[0])


class ProofSlide(SlideView):
    """Named proof rows with the existing shared rail and first-line alignment."""
    row_gap=.17

    def __init__(self, title=None, *, profile="compact", **kwargs):
        self.frame = ProofFrame(profile, theme=kwargs.get("theme", DEFAULT_THEME))
        super().__init__(title, **kwargs)
        self.frame.rows['conclusion']=self.layout.footer.center[1]
        self._insert("proof_rail", self.frame.divider, "chrome")

    def add(self, row, value, *, via=(), path_arc=0, font_scale=None,font_reason=None):
        key = str(row).upper().replace("_", " ")
        if key not in self.frame.LABELS and row not in self.frame.rows:
            raise ValueError(f"Unknown proof row: {row!r}")
        key=key if key in self.frame.LABELS else row
        if any(item.slot == key for item in self.items.values()):
            raise ValueError(f"Duplicate proof row: {row!r}; use substitute")
        with self._editing():
            handle = self._insert(row, value, key, via=via, path_arc=path_arc,
                                  font_scale=font_scale,font_reason=font_reason)
            if key in self.frame.LABELS and 'label:'+row not in self.items:
                self._insert("label:"+row, self.frame.labels_by_name[key], "label:"+row)
        return handle

    def label(self,row):
        """Name a proof stage before its content is spoken, without dummy math."""
        key=str(row).upper().replace('_',' ')
        if key not in self.frame.LABELS:raise ValueError('Unknown proof label')
        with self._editing():
            self._insert('label:'+row,self.frame.labels_by_name[key],'label:'+row)
        return self

    def remove(self, name):
        with self._editing():
            self.items.pop("label:"+name, None)
            del self.items[name]
            self.definition_uses.pop(name, None)
        return self

    def _region(self, slot):
        if slot=='conclusion':return self.layout.footer
        if slot == "chrome":
            from .presentation import SlideRegion
            return SlideRegion((0, 0, 0), self.layout.body.width, float(config.frame_height))
        if slot in self.frame.rows and slot in getattr(self,'_proof_regions',{}):
            return self._proof_regions[slot]
        if slot in self.frame.rows or slot.startswith("label:"):
            return self.layout.body
        return super()._region(slot)

    def row_envelopes(self):
        slots=(*self.frame.LABELS,'work')
        minimums={'DEFINITIONS':.9,'work':.75}
        metrics={slot:{'height':minimums.get(slot,.52),'ascent':0.,'descent':0.} for slot in slots}
        for item in self.items.values():
            if item.slot in metrics:
                if isinstance(item.target,MathRow):
                    # Reserve a fraction-sized envelope from the beginning.
                    # A later numerator must not lift an unchanged f(k) or push
                    # it into the row above while preserving its baseline.
                    item.ascent=max(item.ascent,.5*self.typography.equation/33.6)
                    item.descent=max(item.descent,.25*self.typography.equation/33.6)
                row=metrics[item.slot]
                row['height']=max(row['height'],self._height(item))
                if isinstance(item.target,MathRow):
                    row['ascent']=max(row['ascent'],item.ascent)
                    row['descent']=max(row['descent'],item.descent)
        return metrics

    def _plan_rows(self,metrics=None,*,scale=None):
        from .presentation import SlideRegion
        metrics=metrics or getattr(self,'_sequence_proof_envelopes',None) or self.row_envelopes()
        slots=tuple(metrics)
        shared_scale=scale if scale is not None else getattr(self,'_sequence_fit_scales',{}).get('body',1.)
        heights={slot:row['height']*shared_scale for slot,row in metrics.items()}
        available=self.layout.body.height-self.row_gap*(len(slots)-1)
        ratio=min(1.,available/sum(heights.values()))
        top=self.layout.body.center[1]+self.layout.body.height/2
        left=self.frame.left[0]
        width=self.layout.body.center[0]+self.layout.body.width/2-left
        self._proof_regions={}
        for slot in slots:
            height=heights[slot]*ratio
            y=top-height/2
            self.frame.rows[slot]=y
            row=next((item for item in self.items.values() if item.slot==slot),None)
            if row is not None and isinstance(row.target,MathRow):
                ascent=metrics[slot]['ascent']*shared_scale
                descent=metrics[slot]['descent']*shared_scale
                self.frame.rows[slot]-=row.baseline_offset+(ascent-descent)/2
            self._proof_regions[slot]=SlideRegion((left+width/2,y,0),width,height)
            top-=height+self.row_gap

    def _arrange(self):
        fit=next((area['scale'] for area in self._fit_report if area['group']=='body'),1.)
        self._plan_rows(getattr(self,'_row_plan_metrics',None),scale=fit)
        for name, item in self.items.items():
            if item.slot in self.frame.rows:
                _frame_row(self.frame, item)
            elif item.slot not in ("chrome",) and not item.slot.startswith("label:"):
                item.target.move_to(self.layout.region(item.slot).center)
        for name, item in self.items.items():
            if item.slot.startswith("label:"):
                row = self.items.get(item.slot[6:])
                key=item.slot[6:].upper().replace('_',' ')
                target=(self.frame.label_target(row.slot,first_line_of(row.target)) if row is not None
                        else self.frame.labels_by_name[key].copy().set_y(self.frame.rows[key]))
                item.target.become(target)

    def _text_width(self,slot):
        if slot in self.frame.rows:
            return self.layout.body.center[0]+self.layout.body.width/2-self.frame.left[0]
        return super()._text_width(slot)

    def _fit_areas(self):
        # Measure natural content once. Re-measuring already fitted prose in
        # _arrange would shrink its reserved row for a second time.
        self._row_plan_metrics=getattr(self,'_sequence_proof_envelopes',None) or self.row_envelopes()
        self._plan_rows(self._row_plan_metrics)
        areas=[]
        for item in self.items.values():
            if item.slot in self._proof_regions:
                region=self._proof_regions[item.slot]
                areas.append(FitArea('body',[item],region.width,region.height))
            elif item.slot in ('header','footer','conclusion'):
                region=self.layout.footer if item.slot=='conclusion' else self._region(item.slot)
                # A conclusion is another proof sentence, even though its
                # location is the footer. Fit it with its body-text peers.
                areas.append(FitArea('body' if item.slot=='conclusion' else item.slot,
                                     [item],region.width,region.height))
        return areas


class ViewTransition:
    """One identity-based difference between two final compositions."""

    def __init__(self, outgoing, incoming):
        if not isinstance(incoming, SlideView):
            raise TypeError("The destination must be a SlideView")
        incoming.validate()
        self.outgoing, self.incoming = outgoing, incoming
        old = outgoing.items if outgoing is not None else {}
        old_roots = {id(item.object.mobject) for item in old.values()}
        new_roots = {id(item.object.mobject) for item in incoming.items.values()}
        def expand(items, other_roots, *, entering=False):
            expanded = {}
            wrappers = []
            def visit(name, item):
                mob, target = item.object.mobject, item.target
                is_new_copy = entering and item.object.copied_from is not None and id(mob) not in old_roots
                descendants = {id(part) for part in mob.get_family()[1:]}
                layout_group = type(mob) in (Group, VGroup) or getattr(mob,'_algovis_layout_container',False)
                extracting = id(mob) not in other_roots and bool(descendants & other_roots)
                if not is_new_copy and (layout_group or extracting) and mob.submobjects:
                    if mob.has_points():
                        raise ValueError('Extracting children from a painted parent requires a component operation')
                    wrappers.append(mob)
                    for index, (child, child_target) in enumerate(zip(mob.submobjects, target.submobjects)):
                        visit(f'{name}/{index}', replace(item, object=SlideObject(child), target=child_target))
                else:
                    expanded[id(mob)] = (name, item)
            for name, item in items.items(): visit(name, item)
            return expanded, wrappers
        self.old, old_wrappers = expand(old, new_roots)
        self.new, new_wrappers = expand(incoming.items, old_roots, entering=True)
        self._layout_wrappers = old_wrappers
        self.retained = [key for key in self.new if key in self.old]
        self.entering = [key for key in self.new if key not in self.old]
        self.exiting = [key for key in self.old if key not in self.new]
        self.borrowed={}
        for key,(_name,item) in self.new.items():
            prior=self.old[key][1].target if key in self.old else None
            previous=getattr(prior,'_copy_sources',{})
            self.borrowed[key]={term:source for term,source in getattr(item.target,'_copy_sources',{}).items()
                if previous.get(term) is not source or getattr(prior,'slot_tex',{}).get(term)!=item.target.slot_tex[term]}
        self._scheduled = ()
        # Semantic components remain atomic unless a child is explicitly moved
        # out. Layout groups were expanded above, preserving their child IDs.
        for key in self.exiting:
            family = {id(obj) for obj in self.old[key][1].object.mobject.get_family()}
            if family & set(self.entering):
                raise ValueError("A semantic component needs an explicit child extraction")
        for key in self.entering:
            family = {id(obj) for obj in self.new[key][1].object.mobject.get_family()}
            if family & set(self.exiting):
                raise ValueError("A semantic component needs an explicit child extraction")

    def describe(self):
        moves, keep, substitutions, copies, additions = [], [], [], [], []
        for key in self.retained:
            name, item = self.new[key]
            source = self.old[key][1].target
            (keep if _same_picture(source, item.target) else moves).append(name)
            if isinstance(source, MathRow) and source.slot_tex != item.target.slot_tex:
                substitutions.append(name)
        for key in self.entering:
            name, item = self.new[key]
            if item.object.copied_from is not None:
                copies.append(name)
            else:
                additions.append(name)
        return {"keep": keep, "move": moves, "substitute": substitutions,
                "copy": copies, "enter": additions,
                "exit": [self.old[key][0] for key in self.exiting]}

    def animations(self, scene):
        """Prepare only at the spoken cue, after checking ownership and sources."""
        present = {id(obj) for obj in scene.get_mobject_family_members()}
        for key in self.old:
            if key not in present:
                raise ValueError("The outgoing view has absent objects; adopt the visible composition first")
        sources = [self.new[key][1].object.copied_from for key in self.entering
                   if self.new[key][1].object.copied_from is not None]
        sources += [use.source for name, use in self.incoming.definition_uses.items()
                    if id(self.incoming.items[name].object.mobject) in self.retained]
        sources += [source for key,(_name,item) in self.new.items()
                    if item.object.copied_from is None
                    for source in self.borrowed[key].values()]
        def visible_source(source):
            mob = source.mobject
            painted = [part for part in mob.get_family() if part.has_points()]
            return id(mob) in present or (painted and all(id(part) in present for part in painted))
        if any(not visible_source(source) for source in sources):
            missing=[getattr(source.mobject,'tex_string',type(source.mobject).__name__)
                     for source in sources if not visible_source(source)]
            raise ValueError(f'A copy source must already be visible at the transition: {missing}')
        source_family = {id(obj) for source in sources for obj in source.mobject.get_family()}
        copy_owners = {key for key in self.exiting
                       if source_family & {id(obj) for obj in self.old[key][1].object.mobject.get_family()}}
        exits = [FadeOut(self.old[key][1].object.mobject) for key in self.exiting if key not in copy_owners]

        def build_changes():
            motions = []
            # Copy introductions precede any simultaneous retirement of their source.
            for key in self.entering:
                name, item = self.new[key]
                source = item.object.copied_from
                live = item.object.mobject
                _adopt(live, item.target)
                if source is None:
                    term_sources=getattr(item.target,'_copy_sources',{})
                    if term_sources:
                        motions.extend(ApplyDefinition(term_sources[key].mobject,None,part)
                                       if key in term_sources else FadeIn(part)
                                       for key,part in live.parts.items())
                    else:
                        entering=getattr(type(live),'enter_animation',None)
                        motions.append(entering(live) if entering else FadeIn(live))
                else:
                    motions.append(ApplyDefinition(source.mobject, None, live,
                        via=item.via, path_arc=item.path_arc, preserve_destination_layout=True,copy_only=True))
            for key in self.retained:
                name, item = self.new[key]
                live = item.object.mobject
                if isinstance(live, MathRow):
                    use = self.incoming.definition_uses.get(name)
                    borrowed=self.borrowed[key]
                    for term,source in borrowed.items():
                        motions.append(ApplyDefinition(source.mobject,None,item.target.part(term),copy_only=True))
                    if use:
                        arc=use.path_arc
                        # A proof substitution often moves a wide fraction
                        # down and left. Bow toward its destination column,
                        # clear of the unchanged terms to its right.
                        if isinstance(self.incoming,ProofSlide) and not use.via and not arc:
                            source=use.source.mobject;destination=item.target.part(use.part)
                            delta=destination.get_center()-source.get_center()
                            if delta[1]<-.1 and abs(delta[0])>.1:
                                from manim.utils.paths import path_along_arc
                                candidate=float(np.sign(delta[0])*np.pi/2)
                                path=path_along_arc(candidate)
                                centers=[path(source.get_center()[None,:],destination.get_center()[None,:],alpha)[0]
                                         for alpha in np.linspace(0,1,21)]
                                left=self.incoming.frame.left[0]
                                right=self.incoming.layout.body.width/2
                                if all(left<=point[0]-source.width/2 and point[0]+source.width/2<=right for point in centers):
                                    arc=candidate
                        motions.append(ApplyDefinition(use.source.mobject, live.part(use.part),
                            item.target.part(use.part), via=use.via, path_arc=arc,
                            preserve_destination_layout=True))
                    skip = tuple(borrowed)+((use.part,) if use else ())
                    motions += [animation for animation in live.motions_to(item.target, skip=skip)
                                if not hasattr(animation, "target_mobject")
                                or not _same_picture(animation.mobject, animation.target_mobject)]
                elif hasattr(type(live),'motions_to') and hasattr(type(live),'adopt_layout'):
                    use=self.incoming.definition_uses.get(name)
                    if use:
                        def at_path(root,path):
                            for part in path.split('.'):root=root.part(part)
                            return root
                        destination=at_path(item.target,use.part)
                        route=getattr(type(self.incoming),'definition_route',None)
                        via=use.via or (route(self.incoming,use.source.mobject,destination) if route else ())
                        motions.append(ApplyDefinition(use.source.mobject,at_path(live,use.part),
                            destination,via=via,path_arc=use.path_arc,preserve_destination_layout=True))
                        motions.extend(live.motions_to(item.target,skip=(use.part,)))
                    elif not _same_picture(live,item.target):motions.extend(live.motions_to(item.target))
                elif not _same_picture(live, item.target):
                    motions.append(Transform(live, item.target, path_arc=item.path_arc))
            changing = AnimationGroup(*motions) if motions else Wait(.001)
            if copy_owners:
                # The definition stays visible until its copy has arrived.
                return Succession(changing, _deferred(lambda: AnimationGroup(
                    *(FadeOut(self.old[key][1].object.mobject) for key in copy_owners)), run_time=.2))
            return changing

        if exits:
            if not self.entering and not self.retained and not copy_owners:
                self._scheduled = tuple(exits)
            else:
                self._scheduled = (Succession(
                    _deferred(lambda: AnimationGroup(*exits), run_time=.25),
                    _deferred(build_changes, run_time=.75)),)
        elif (not self.incoming.definition_uses
                and not any(self.describe()[kind] for kind in ("move", "substitute", "copy", "enter", "exit"))):
            self._scheduled = ()
        else:
            self._scheduled = (_deferred(build_changes),)
        return self._scheduled

    def commit(self, scene, *, adopt=True, consolidate=True):
        # AnimationGroup and Succession build synthetic owners. A nested copy
        # can dissolve those groups, leaving an empty wrapper at the scene root.
        # Retire only this transition's wrappers, then restore one artwork owner.
        def retire_wrappers(animation):
            if isinstance(animation, (AnimationGroup, DeferredAnimation)):
                scene.remove(animation.mobject)
            for child in getattr(animation, 'animations', ()):
                retire_wrappers(child)
            if isinstance(animation, DeferredAnimation) and animation.animation is not None:
                retire_wrappers(animation.animation)
        for animation in self._scheduled:
            retire_wrappers(animation)
        for key in self.exiting:
            scene.remove(*self.old[key][1].object.mobject.get_family())
        for key, (name, item) in self.new.items():
            live = item.object.mobject
            if not adopt:
                continue
            if key in self.retained and isinstance(live, MathRow):
                live.commit(item.target, scene)
            elif key in self.retained and hasattr(type(live),'adopt_layout'):
                scene.remove(*live.get_family(),*item.target.get_family())
                live.adopt_layout(item.target)
            for old, new in zip(live.get_family(), item.target.get_family()):
                _copy_layout_metadata(new,old)
            live._algovis_view_fit_scale=getattr(item.target,'_algovis_view_fit_scale',1.)
        # Remove dissolved child roots before restoring exactly one owner.
        if consolidate:
            scene.remove(*self._layout_wrappers)
            for key, (name, item) in self.new.items():
                scene.remove(*item.object.mobject.get_family())
            scene.add(*(item.object.mobject for item in self.incoming.items.values()))
        if hasattr(scene, "_capture_review_snapshot"):
            scene._capture_review_snapshot()


def _adopt(live, target):
    if hasattr(type(live),'adopt_layout'):
        live.adopt_layout(target)
    elif isinstance(live,Group) and not isinstance(live,VGroup):
        # Group supports raster/vector composition but its unpainted root has
        # no color interpolator. Adopt the actual children, as Transform does,
        # without calling Mobject.become on that layout-only root.
        if len(live.submobjects)!=len(target.submobjects):
            raise ValueError('Changing a mixed component’s children requires its own adoption protocol')
        for child,destination in zip(live.submobjects,target.submobjects):_adopt(child,destination)
    else:
        live.become(target)
    for old, new in zip(live.get_family(), target.get_family()):
        _copy_layout_metadata(new,old)
    live._algovis_view_fit_scale=getattr(target,'_algovis_view_fit_scale',1.)


def _copy_layout_metadata(source,destination):
    copy_semantics(source,destination)
    if hasattr(source,'_algovis_relative_font_scale'):
        destination._algovis_relative_font_scale=source._algovis_relative_font_scale
    if hasattr(source,'_algovis_font_scale_reason'):
        destination._algovis_font_scale_reason=source._algovis_font_scale_reason
    if isinstance(source,Text) and isinstance(destination,Text):
        # Reflow changes the block height, not its font size. Manim's geometric
        # become/Transform does not adopt these Pango font-reference fields.
        destination.original_text=source.original_text
        destination.text=source.text
        destination._font_size=source._font_size
        destination.initial_height=source.initial_height
        for name in ('_algovis_source_text','_algovis_label'):
            if hasattr(source,name):setattr(destination,name,getattr(source,name))
    if getattr(source,'_algovis_scene_typography',False):
        from .layout import LessonStyle, measured_font_size
        destination._algovis_scene_typography=True
        LessonStyle._watch_type(destination,source._algovis_typography_group,
                                source._algovis_type_role,measured_font_size(source))


def _frame_fit_areas(view, rows, left):
    top=view.layout.body.center[1]+view.layout.body.height/2
    bottom=view.layout.body.center[1]-view.layout.body.height/2
    anchors=sorted({float(rows[item.slot]) for item in view.items.values() if item.slot in rows})
    areas=[]
    for item in view.items.values():
        if item.slot=='conclusion':
            region=view.layout.footer
            areas.append(FitArea('footer',[item],region.width,region.height))
        elif item.slot in rows:
            y=rows[item.slot]
            upper=min([top,*[other for other in anchors if other>y]])
            lower=max([bottom,*[other for other in anchors if other<y]])
            height=max(.01,min(upper-y,y-lower)*2-.14)
            width=view.layout.body.center[0]+view.layout.body.width/2-left
            areas.append(FitArea('body',[item],width,height))
        elif item.slot in ('header','footer'):
            region=view._region(item.slot)
            areas.append(FitArea(item.slot,[item],region.width,region.height))
    return areas


def _column_row(column, name, item):
    if not isinstance(item.target, MathRow):
        column.add(name, item.target)
        return
    target = item.target
    ascent = float(target.get_top()[1]-target.baseline)
    descent = float(target.baseline-target.get_bottom()[1])
    # Reserve both halves of a growing equation. Simplifying a fraction later
    # cannot pull its unchanged function call or subsequent rows upward.
    item.ascent = max(item.ascent, ascent)
    item.descent = max(item.descent, descent)
    column.add(name, target, height=item.ascent+item.descent)
    target.shift([0, ascent-item.ascent, 0])


def _frame_row(frame, item):
    frame.place(item.slot, item.target)
    if isinstance(item.target, MathRow):
        baseline = frame.anchor(item.slot)[1]+item.baseline_offset
        item.target.shift([0, baseline-item.target.baseline, 0])


def _deferred(factory, **kwargs):
    animation = DeferredAnimation(factory, **kwargs)
    animation._algovis_view_transition = True
    return animation
