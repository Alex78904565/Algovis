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

import numpy as np
from manim import AnimationGroup, FadeIn, FadeOut, Group, Mobject, Succession, Text, Transform, VGroup, Wait, config

from .core.math import ApplyDefinition
from .core.math_row import MathRow
from .core.proof import first_line_of
from .frames import EquationFrame, ProofFrame
from .layout import ColumnLayout
from .fitting import FitArea, FitPolicy, plain_text, relative_font_scale
from .semantics import copy_semantics
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
        return SlideObject(self.mobject.copy(), copied_from=self)

    def part(self, name):
        """Select a stable named mathematical term as a copy source."""
        if not isinstance(self.mobject, MathRow):
            raise TypeError("Named terms require a MathRow")
        part = self.mobject.part(name)
        part._view_attention_term = True
        return SlideObject(part)

    def on_word(self, cue, *, style='auto', reason, duration=.45, callback=None):
        """Declare attention once; ViewSceneMixin schedules its spoken trigger."""
        from .attention import attention_declaration
        binding = attention_declaration(self.mobject, cue, style=style, reason=reason,
                                        duration=duration, callback=callback)
        declarations = list(getattr(self.mobject, '_view_word_attention', ()))
        declarations.append(binding)
        self.mobject._view_word_attention = declarations
        self.mobject._view_attention_owner = id(self.mobject)
        return self


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
            if x is None or y is None:
                if x is not y:
                    return False
                continue
            x, y = np.asarray(x), np.asarray(y)
            if x.shape != y.shape or not np.allclose(x, y, atol=1e-9, rtol=0):
                return False
    return True


class SlideView:
    """A final composition built from detached targets and stable live objects."""

    def __init__(self, title=None, *, theme=DEFAULT_THEME, layout=None, auto_fit=True):
        from .presentation import Slide, SlideLayout
        self.theme = theme
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

    def target(self, name):
        """The detached final artwork, useful for inspecting or styling a view."""
        return self.items[name].target

    def _insert(self, name, value, slot, *, via=(), path_arc=0, font_scale=None):
        if name in self.items:
            raise ValueError(f"Duplicate slide item: {name!r}; use move or substitute")
        if isinstance(value,str):
            value = plain_text(value,self._text_width(slot),theme=self.theme,
                               wrap=self.fit_policy.enabled and self.fit_policy.wrap_text)
        handle = _object(value)
        target = handle.mobject.copy()
        prior_fit = getattr(target,'_algovis_view_fit_scale',1.)
        if prior_fit != 1:
            target.scale(1/prior_fit)
        target._algovis_view_fit_scale = 1.
        inherited=getattr(target,'_algovis_relative_font_scale',1.)
        factor=inherited if font_scale is None else float(font_scale)
        relative_font_scale(target,factor)
        target.scale(factor/inherited)
        metrics = {}
        if isinstance(target, MathRow):
            metrics = dict(ascent=float(target.get_top()[1]-target.baseline),
                           descent=float(target.baseline-target.get_bottom()[1]),
                           baseline_offset=float(target.baseline-target.get_y()))
        self.items[name] = Placement(handle, target, slot, tuple(via), path_arc, font_scale=factor, **metrics)
        return handle

    @contextmanager
    def _editing(self):
        # Layout failure must not leave a partly rearranged future slide.
        previous, previous_uses = self.items, self.definition_uses
        previous_defaults, previous_warnings = self._default_centers, set(self._warned_offsets)
        previous_fit = self._fit_report
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
            raise

    def add(self, name, value, *, region="body", via=(), path_arc=0, font_scale=None):
        """Place an object in a named safe region without touching the live one."""
        with self._editing():
            handle = self._insert(name, value, region, via=via, path_arc=path_arc,font_scale=font_scale)
        return handle

    def set_font_scale(self, name, factor):
        """Change a text size relative to its natural role, without coordinates."""
        factor=float(factor)
        with self._editing():
            item=self.items[name]
            relative_font_scale(item.target,factor)
            self._scale_item(item,factor/item.font_scale)
            item.font_scale=factor
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
                        wrapped=plain_text(source,self._text_width(item.slot)/item.font_scale,theme=self.theme)
                        copy_semantics(item.target,wrapped)
                        wrapped.scale(item.font_scale)
                        item.target=wrapped
            for item in self.items.values():relative_font_scale(item.target,item.font_scale)
            areas=self._fit_areas();scales={}
            for area in areas:
                scales[area.group]=min(scales.get(area.group,1.),area.scale(self._height))
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

    def add(self, row, value, *, via=(), path_arc=0, font_scale=None):
        if row not in self.frame.rows:
            raise ValueError(f"Unknown equation row: {row!r}")
        return super().add(row, value, region=row, via=via, path_arc=path_arc,font_scale=font_scale)

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

    def __init__(self, title=None, *, profile="compact", **kwargs):
        self.frame = ProofFrame(profile, theme=kwargs.get("theme", DEFAULT_THEME))
        super().__init__(title, **kwargs)
        self._insert("proof_rail", self.frame.divider, "chrome")

    def add(self, row, value, *, via=(), path_arc=0, font_scale=None):
        key = str(row).upper().replace("_", " ")
        if key not in self.frame.LABELS:
            raise ValueError(f"Unknown proof row: {row!r}")
        if any(item.slot == key for item in self.items.values()):
            raise ValueError(f"Duplicate proof row: {row!r}; use substitute")
        with self._editing():
            handle = self._insert(row, value, key, via=via, path_arc=path_arc,font_scale=font_scale)
            self._insert("label:"+row, self.frame.labels_by_name[key], "label:"+row)
        return handle

    def remove(self, name):
        with self._editing():
            self.items.pop("label:"+name, None)
            del self.items[name]
            self.definition_uses.pop(name, None)
        return self

    def _region(self, slot):
        if slot == "chrome":
            from .presentation import SlideRegion
            return SlideRegion((0, 0, 0), self.layout.body.width, float(config.frame_height))
        if slot in self.frame.LABELS or slot.startswith("label:"):
            return self.layout.body
        return super()._region(slot)

    def _arrange(self):
        for name, item in self.items.items():
            if item.slot in self.frame.LABELS:
                _frame_row(self.frame, item)
            elif item.slot not in ("chrome",) and not item.slot.startswith("label:"):
                item.target.move_to(self.layout.region(item.slot).center)
        for name, item in self.items.items():
            if item.slot.startswith("label:"):
                row = self.items[item.slot[6:]]
                target = self.frame.label_target(row.slot, first_line_of(row.target))
                item.target.become(target)

    def _text_width(self,slot):
        if slot in self.frame.LABELS:
            return self.layout.body.center[0]+self.layout.body.width/2-self.frame.left[0]
        return super()._text_width(slot)

    def _fit_areas(self):
        return _frame_fit_areas(self,self.frame.rows,self.frame.left[0])


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
                layout_group = type(mob) in (Group, VGroup)
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
        def visible_source(source):
            mob = source.mobject
            painted = [part for part in mob.get_family() if part.has_points()]
            return id(mob) in present or (painted and all(id(part) in present for part in painted))
        if any(not visible_source(source) for source in sources):
            raise ValueError("A copy source must already be visible at the transition")
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
                    motions.append(FadeIn(live))
                else:
                    motions.append(ApplyDefinition(source.mobject, None, live,
                        via=item.via, path_arc=item.path_arc, preserve_destination_layout=True))
            for key in self.retained:
                name, item = self.new[key]
                live = item.object.mobject
                if isinstance(live, MathRow):
                    use = self.incoming.definition_uses.get(name)
                    if use:
                        motions.append(ApplyDefinition(use.source.mobject, live.part(use.part),
                            item.target.part(use.part), via=use.via, path_arc=use.path_arc,
                            preserve_destination_layout=True))
                    skip = (use.part,) if use else ()
                    motions += [animation for animation in live.motions_to(item.target, skip=skip)
                                if not hasattr(animation, "target_mobject")
                                or not _same_picture(animation.mobject, animation.target_mobject)]
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
    if isinstance(live, MathRow):
        live.adopt_layout(target)
    else:
        live.become(target)
    for old, new in zip(live.get_family(), target.get_family()):
        _copy_layout_metadata(new,old)
    live._algovis_view_fit_scale=getattr(target,'_algovis_view_fit_scale',1.)


def _copy_layout_metadata(source,destination):
    copy_semantics(source,destination)
    if hasattr(source,'_algovis_relative_font_scale'):
        destination._algovis_relative_font_scale=source._algovis_relative_font_scale
    if isinstance(source,Text) and isinstance(destination,Text):
        # Reflow changes the block height, not its font size. Manim's geometric
        # become/Transform does not adopt these Pango font-reference fields.
        destination.original_text=source.original_text
        destination.text=source.text
        destination._font_size=source._font_size
        destination.initial_height=source.initial_height
        for name in ('_algovis_source_text','_algovis_label'):
            if hasattr(source,name):setattr(destination,name,getattr(source,name))


def _frame_fit_areas(view, rows, left):
    top=view.layout.body.center[1]+view.layout.body.height/2
    bottom=view.layout.body.center[1]-view.layout.body.height/2
    anchors=sorted({float(rows[item.slot]) for item in view.items.values() if item.slot in rows})
    areas=[]
    for item in view.items.values():
        if item.slot in rows:
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
