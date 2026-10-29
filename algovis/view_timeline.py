"""Cue-driven view timelines for diagrams and progressive mathematical boards.

Layout groups have no independent painted identity. Their children can leave a
group, be retained elsewhere, and regroup without copying or disappearing. The
timeline compiles each phase to a detached CanvasSlide and a ViewTransition.
Manim remains the interpolation backend, including for component-owned effects.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import numpy as np
from manim import (
    Animation, AnimationGroup, Create, FadeIn, FadeOut, Group, GrowArrow,
    GrowFromCenter, LaggedStart, MoveAlongPath, ReplacementTransform, Succession,
    Transform, TransformFromCopy, VGroup, Wait, Write,
)
from manim.animation.animation import prepare_animation

from .composition import Placement, SlideObject, SlideView, ViewTransition
from .core.math import ApplyDefinition
from .core.math_row import MathRow
from .utils.effects import DeferredAnimation, ReplaceContent
from .attention import attention_declaration


# These are authoring operations, consumed by ViewSceneMixin's compiler. The
# native bases preserve Manim's familiar easing, duration and drawing options.
class Reveal(FadeIn):
    """Add artwork to the next view, retaining any children already on stage."""


class Retire(FadeOut):
    """Omit artwork from the next view; an absent object stays absent."""


class Move(Transform):
    """A retained object's next geometry, with the same object identity."""

    def begin(self):
        super().begin()
        from .layout import measured_font_size
        self._font_motions = []
        for live, start, end in zip(self.mobject.get_family(),
                                    self.starting_mobject.get_family(),
                                    self.target_mobject.get_family()):
            if hasattr(start, '_algovis_font_reference'):
                a, b = measured_font_size(start), measured_font_size(end)
                if a is not None and b is not None:
                    self._font_motions.append((live, a, b))

    def interpolate(self, alpha):
        super().interpolate(alpha)
        # During a glyph morph, ink height is not a font-size measurement.
        # Another simultaneous operation can snapshot this halfway through.
        # Calibrate against the intended interpolated point size on every frame.
        progress = self.rate_func(alpha)
        for live, start, end in getattr(self, '_font_motions', ()):
            if live.height > 0:
                live._algovis_font_reference = (start+(end-start)*progress, float(live.height))

    def finish(self):
        super().finish()
        # Transform adopts points, but not the font calibration attached to
        # the typeset glyph. An i becoming k must keep the destination's point
        # size even though those letters have different ink heights.
        from .composition import _copy_layout_metadata
        for live, target in zip(self.mobject.get_family(), self.target_mobject.get_family()):
            _copy_layout_metadata(target, live)
            if hasattr(target, '_algovis_font_reference'):
                live._algovis_font_reference = target._algovis_font_reference
            if hasattr(target, 'initial_height') and hasattr(target, 'tex_string'):
                live.initial_height = target.initial_height


class CopyInto(TransformFromCopy):
    def __init__(self, source, target, **kwargs):
        self.view_source, self.view_target = source, target
        super().__init__(source, target, **kwargs)


class Replace(ReplaceContent):
    """Two view phases: retire the old statement, then reveal its replacement."""


class ReplaceShape(ReplacementTransform):
    """An explicit change of object identity while morphing its artwork."""


class Draw(Create):
    pass


class WriteView(Write):
    pass


class Grow(GrowFromCenter):
    pass


class DrawArrow(GrowArrow):
    pass


class Together(AnimationGroup):
    pass


class Then(Succession):
    pass


class Stagger(LaggedStart):
    pass


class Later(DeferredAnimation):
    """Plan a later phase only after its prerequisites have finished."""


def _layout_group(mob):
    return type(mob) in (Group, VGroup)


def _cut(mob, focus=()):
    """Find painted ownership roots without modifying component hierarchies."""
    members = {id(part) for part in mob.get_family()}
    split = _layout_group(mob) or (id(mob) not in focus and bool(members & set(focus)))
    if split and mob.submobjects:
        if mob.has_points():
            raise ValueError('A painted parent needs an explicit component operation before extracting its children')
        return [part for child in mob.submobjects for part in _cut(child, focus)]
    return [mob] if mob.has_points() or mob.submobjects else []


def _unique_roots(roots):
    result, seen = [], set()
    # Keep a semantic component instead of also painting its registered child.
    contained = {id(child) for root in roots for child in root.get_family()[1:]}
    for root in roots:
        if id(root) in seen or id(root) in contained:
            continue
        result.append(root)
        seen.update(id(part) for part in root.get_family())
    return result


def _normalize(scene, focus=()):
    roots = [part for root in scene.mobjects for part in _cut(root, focus)]
    scene.mobjects = _unique_roots(roots)


class CanvasSlide(SlideView):
    """A board of positioned components, using their own shared layout frames.

    A tree, proof frame or road diagram decides its internal geometry. Unlike a
    column, a canvas does not reinterpret those endpoints or independently shrink
    a mathematical row. Overlap within diagram envelopes is intentional; the
    production ink-level audit checks actual text/painted bounds.
    """

    def _arrange(self):
        pass

    def add(self, *args, **kwargs):
        raise TypeError('Use ColumnSlide, SplitSlide, EquationSlide or ProofSlide for automatic alignment; '
                        'CanvasSlide.include explicitly retains a component\'s existing layout')

    def validate(self):
        seen = set()
        for item in self.items.values():
            family = {id(part) for part in item.object.mobject.get_family()}
            if family & seen:
                raise ValueError('A canvas cannot paint a child through two owners')
            seen.update(family)
            if not np.isfinite(item.target.get_all_points()).all():
                raise ValueError('Canvas geometry must be finite')
        return self

    @classmethod
    def capture(cls, scene):
        view = cls(theme=scene.theme)
        for mob in scene.mobjects:
            if getattr(mob, '_view_external', False):
                continue
            view.include(scene.view_name(mob), mob)
        return view

    def include(self, name, mob, target=None):
        self.items[name] = Placement(SlideObject(mob), (target if target is not None else mob).copy(), 'body')
        return self.items[name].object


def _incoming_roots(mob, present):
    family = {id(part) for part in mob.get_family()}
    split = _layout_group(mob) or (id(mob) not in present and bool(family & present))
    if split and mob.submobjects:
        if mob.has_points():
            raise ValueError('A painted parent cannot implicitly take ownership of existing children')
        return [part for child in mob.submobjects for part in _incoming_roots(child, present)]
    return [mob] if mob.has_points() or mob.submobjects else []


def _kind(animation):
    if isinstance(animation, ApplyDefinition): return 'definition_copy'
    if isinstance(animation, TransformFromCopy): return 'copy'
    if isinstance(animation, FadeOut): return 'retire'
    if isinstance(animation, ReplacementTransform): return 'replace_shape'
    if getattr(animation, '_algovis_attention', None) or getattr(animation, '_algovis_focus_target', None):
        return 'component_effect'
    rate = getattr(animation, 'rate_func', None)
    if isinstance(animation, Transform) and rate is not None and abs(float(rate(1))) < 1e-7:
        return 'component_effect'
    if animation.is_introducer() or isinstance(animation, (Create, Write, GrowArrow, GrowFromCenter)):
        return 'reveal'
    if isinstance(animation, Transform): return 'move'
    if isinstance(animation, Wait): return 'hold'
    return 'component_effect'


def _references(animation):
    if isinstance(animation, ApplyDefinition):
        return [animation.definition, animation.application, animation.result]
    if isinstance(animation, CopyInto): return [animation.view_source, animation.view_target]
    if isinstance(animation, TransformFromCopy):
        return [animation.target_mobject, animation.mobject]
    return [animation.mobject]


def _needs_math_layout(animation):
    return (_kind(animation) == 'move'
            and any(isinstance(part, MathRow) for part in animation.mobject.get_family()))


class _GatedPhase(DeferredAnimation):
    """AnimationGroup.begin is eager; activate only at the first timed frame."""

    def begin(self):
        self._activated = False
        self._inner_cleaned = False

    def _activate(self):
        if not self._activated:
            self._activated = True
            super().begin()

    def interpolate(self, alpha):
        self._activate()
        super().interpolate(alpha)

    def finish(self):
        self._activate()
        super().finish()


class _ViewPhase(_GatedPhase):
    def __init__(self, scene, operations, *, clear_first=False, **kwargs):
        self.host, self.operations = scene, operations
        self.clear_first = clear_first
        self.plan = None
        self.record = None
        self._committed = False
        super().__init__(self._prepare, **kwargs)
        self._algovis_view_transition = True

    def _prepare(self):
        scene = self.host
        refs = [mob for operation in self.operations for mob in _references(operation) if mob is not None]
        # Selected terms become independent ownership roots. Groups retain all
        # their Python child references, so component methods still address them.
        focus = {id(part) for mob in refs for part in _cut(mob)}
        _normalize(scene, focus)
        outgoing = CanvasSlide.capture(scene)
        incoming = outgoing.fork()
        present = {id(part) for mob in scene.mobjects for part in mob.get_family()}
        animations = []
        source_names = []

        def omit(mob):
            if mob is None: return
            ids = {id(part) for part in mob.get_family()}
            incoming.items = type(incoming.items)((name, item) for name, item in incoming.items.items()
                                                if id(item.object.mobject) not in ids)

        def include(mob):
            for part in _incoming_roots(mob, present):
                incoming.include(scene.view_name(part), part)

        for operation in self.operations:
            kind = _kind(operation)
            if kind == 'retire':
                omit(operation.mobject)
                available = [item.object.mobject for item in outgoing.items.values()
                             if id(item.object.mobject) in {id(p) for p in operation.mobject.get_family()}]
                if not available:
                    continue
                operation.mobject = available[0] if len(available) == 1 else Group(*available)
            elif kind == 'reveal':
                include(operation.mobject)
            elif kind == 'definition_copy':
                omit(operation.application)
                include(operation.result)
                source_names.append(scene.view_name(operation.definition))
            elif kind == 'copy':
                source, target = (_references(operation))
                include(target)
                source_names.append(scene.view_name(source))
                operation = ApplyDefinition(source, None, target, preserve_destination_layout=True,
                                            run_time=operation.run_time,
                                            path_arc=getattr(operation, 'path_arc', 0))
            elif kind == 'replace_shape':
                omit(operation.mobject)
                include(operation.target_mobject)
            elif kind == 'move':
                # Plan on detached artwork; native interpolation preserves the
                # established per-component easing and property-adoption hooks.
                original = operation.mobject
                planned = original.copy()
                correspondence = dict(zip((id(p) for p in original.get_family()), planned.get_family()))
                # Group can contain both raster and vector artwork. Its base
                # Mobject has no color interpolator, so become() is not a valid
                # layout planner. Use Manim's own point-bearing-family transform
                # on detached copies, just as the eventual motion does.
                planning_motion = Transform(planned, operation.target_mobject.copy())
                planning_motion.begin()
                planning_motion.finish()
                for name, item in incoming.items.items():
                    target = correspondence.get(id(item.object.mobject))
                    if target is not None:
                        incoming.items[name] = replace(item, target=target.copy())
            animations.append(operation)

        incoming.validate()
        self.plan = ViewTransition(outgoing, incoming)
        diff = self.plan.describe()
        self.record = {'start': float(scene.renderer.time), 'cue': getattr(scene, '_review_active_cue', {}).get('cue'),
                       'operations': [_kind(a) for a in self.operations], 'difference': diff,
                       'copySources': source_names, 'layout': 'CanvasSlide', 'completed': False}
        scene._view_steps.append(self.record)
        if not animations:
            actual = Wait(.001)
        elif self.clear_first:
            exits = [a for a in animations if isinstance(a, FadeOut)]
            rest = [a for a in animations if not isinstance(a, FadeOut)]
            actual = (Succession(AnimationGroup(*exits), AnimationGroup(*rest))
                      if exits and rest else AnimationGroup(*animations))
        else:
            actual = AnimationGroup(*animations)
        # Native motion is a policy for this view difference, not another scene
        # lifecycle. The same plan owns retirement, copies and endpoint records.
        self.plan._scheduled = (actual,)
        return actual

    def _commit(self):
        if self._committed or self.plan is None: return
        # Dissolve synthetic animation wrappers before retiring them. Removing
        # a wrapper while it still owns a retained child would erase that child.
        _normalize(self.host)
        self.plan.commit(self.host, adopt=False, consolidate=False)
        _normalize(self.host)
        self.host.current_view = CanvasSlide.capture(self.host)
        self.record.update(end=float(self.host.renderer.time), completed=True,
                           objects=list(self.host.current_view.items))
        self._committed = True

    def finish(self):
        super().finish()
        self._commit()

    def clean_up_from_scene(self, scene):
        super().clean_up_from_scene(scene)
        self._commit()


class _MathLayoutPhase(_GatedPhase):
    """Use named equation terms when a containing layout moves or substitutes.

    Native Transform aligns raw subobject counts, including invisible baseline
    anchors. A mathematical row instead owns its terms and adopts its new native
    layout after their motion. Layout-only parents preserve that child identity.
    """

    def __init__(self, scene, animation):
        self.host = scene
        self.adoptions = []

        def lower(source, target):
            if isinstance(source, MathRow):
                if not isinstance(target, MathRow):
                    raise TypeError('A named MathRow needs a MathRow destination; use next_layout for substitutions')
                if getattr(source, '_algovis_typography_group', None):
                    from .layout import LessonStyle
                    LessonStyle._watch_type(target, source._algovis_typography_group, 'equation')
                self.adoptions.append((source, target))
                return [Move(motion.mobject, motion.target_mobject)
                        if isinstance(motion, Transform) else motion
                        for motion in source.motions_to(target)]
            if any(isinstance(part, MathRow) for part in source.get_family()):
                if source.has_points() or target.has_points():
                    raise ValueError('A painted parent needs a component operation to change its named equations')
                if len(source) != len(target):
                    raise ValueError('Changing layout children needs explicit reveal/retire operations')
                return [motion for child, destination in zip(source, target)
                        for motion in lower(child, destination)]
            return [Move(source, target, run_time=animation.run_time,
                         rate_func=animation.rate_func,
                         path_arc=getattr(animation, 'path_arc', 0))]

        operations = lower(animation.mobject, animation.target_mobject)
        for operation in operations:
            operation.set_run_time(animation.run_time)
            operation.rate_func = animation.rate_func
        super().__init__(lambda: scene._compile_view(Together(*operations,
            run_time=animation.run_time)),
            run_time=animation.run_time)
        self._algovis_view_transition = True

    def finish(self):
        super().finish()
        for row, target in self.adoptions:
            row.commit(target, self.host)
        _normalize(self.host)
        self.host.current_view = CanvasSlide.capture(self.host)


class ViewSceneMixin:
    """Every narrated event is compiled as a view phase or a view sequence."""

    def setup(self):
        super().setup()
        self._view_steps = []
        self._view_names = {}
        self._view_name_counter = 0
        self._word_attention = []
        self._attention_waiting = False

    def begin_narration(self, *args, **kwargs):
        self._word_attention = []
        return super().begin_narration(*args, **kwargs)

    def bind_attention(self, target, cue, **options):
        target = target.mobject if isinstance(target, SlideObject) else target
        binding = attention_declaration(target, cue, **options)
        self._validate_attention_registration(binding)
        self._word_attention.append(binding)
        return binding

    def _validate_attention_registration(self, binding):
        if self.narration is None or self.narration.start_time is None: return
        time = self.narration.word_anchor(binding.cue)['start']
        tolerance = 1/float(self.camera.frame_rate)+.015
        if self.narration.elapsed(self)-time > tolerance:
            raise ValueError(f'Attention {binding.cue!r} was registered after its word was spoken')

    def _discover_attention(self, operations=()):
        mobs = list(self.mobjects)
        for operation in operations:
            animation = prepare_animation(operation)
            mobs += [mob for mob in _references(animation) if mob is not None]
        known = {id(binding) for binding in self._word_attention}
        for mob in mobs:
            for part in mob.get_family():
                if getattr(part, '_view_attention_owner', None) != id(part): continue
                for binding in getattr(part, '_view_word_attention', ()):
                    if id(binding) not in known:
                        self._validate_attention_registration(binding)
                        self._word_attention.append(binding)
                        known.add(id(binding))

    def _attention_programs(self, name, operations, duration, edge, *, start_override=None):
        self._discover_attention(operations)
        if self.narration is None: return ()
        start = (self.narration.word_anchor(name)[edge] if start_override is None else start_override)
        programs = []
        for binding in self._word_attention:
            if binding.fired: continue
            anchor = self.narration.word_anchor(binding.cue)
            delay = anchor['start']-start
            if delay < -.001 or delay >= duration-.001: continue
            present = {id(part) for part in self.get_mobject_family_members()}
            revealing = any(_kind(prepare_animation(operation)) == 'reveal'
                            and binding.target in prepare_animation(operation).mobject.get_family()
                            for operation in operations)
            if revealing and id(binding.target) not in present and binding.callback is None:
                binding.fired = True  # The reveal itself supplies the attention.
                continue
            if delay+binding.duration > duration+.001:
                raise ValueError(f'Attention {binding.cue!r} exceeds its animation slot; shorten it or give it its own cue')
            binding.fired = True
            effect = Later(lambda binding=binding: binding.animation(self), run_time=binding.duration)
            effect._view_word_trigger = {'cue':binding.cue,'time':anchor['start'],
                'trigger':self.narration.cues[binding.cue].phrase,'reason':binding.reason,
                'narrationStart':self.narration.start_time}
            pieces = ([Wait(delay)] if delay > .001 else [])+[effect]
            remaining = duration-delay-binding.duration
            if remaining > .001: pieces.append(Wait(remaining))
            programs.append(Then(*pieces, run_time=duration))
        return tuple(programs)

    def view_name(self, mob):
        key = id(mob)
        if key not in self._view_names:
            self._view_name_counter += 1
            label = self._review_object_label(mob).replace('\n', ' ')[:65]
            self._view_names[key] = f'{label or type(mob).__name__}:{self._view_name_counter}'
        return self._view_names[key]

    def mount_view(self, *objects):
        """Adopt prepared component artwork or consolidate a completed phase."""
        super().add(*objects)
        _normalize(self)
        self.current_view = CanvasSlide.capture(self)
        return self

    def unmount_view(self, *objects):
        """Retire already-completed component artwork without reviving siblings."""
        # A layout container may already have dissolved into independent scene
        # roots. Native Scene.remove(container) only removes that exact owner;
        # explicitly retire its family so a section handoff cannot leave ghosts.
        super().remove(*(part for mob in objects for part in mob.get_family()))
        _normalize(self)
        self.current_view = CanvasSlide.capture(self)
        return self

    def reset_views(self):
        super().clear()
        self.current_view = None
        return self

    def _compile_view(self, specification):
        compiled = self._compile_view_native(specification)
        compiled._view_compiled = True
        return compiled

    def _compile_view_native(self, specification):
        animation = prepare_animation(specification)
        if (isinstance(animation, ApplyDefinition) or getattr(animation, '_algovis_attention', None)
                or getattr(animation, '_algovis_focus_target', None)):
            return _ViewPhase(self, (animation,), run_time=animation.run_time)
        if isinstance(animation, DeferredAnimation):
            later = _GatedPhase(lambda: self._compile_view(animation.factory()), run_time=animation.run_time)
            later._algovis_view_transition = True
            if hasattr(animation, '_view_word_trigger'):
                later._view_word_trigger = animation._view_word_trigger
            return later
        if isinstance(animation, AnimationGroup):
            children = animation.animations
            if not children:
                return Wait(animation.run_time)
            if not isinstance(animation, Succession) and not animation.lag_ratio and all(
                    not isinstance(child, (AnimationGroup, DeferredAnimation))
                    or isinstance(child, ApplyDefinition) for child in children) and not any(
                        _needs_math_layout(child) for child in children):
                return _ViewPhase(self, tuple(children), run_time=animation.run_time)
            cls = Succession if isinstance(animation, Succession) else AnimationGroup
            return cls(*(self._compile_view(child) for child in children),
                       lag_ratio=animation.lag_ratio, run_time=animation.run_time,
                       rate_func=animation.rate_func)
        if _needs_math_layout(animation):
            return _MathLayoutPhase(self, animation)
        return _ViewPhase(self, (animation,), run_time=animation.run_time)

    def _view_program(self, operations, run_time, *, clear_first=False, attention=(), force_runtime=True):
        operations = tuple(prepare_animation(operation) for operation in operations)
        def compiled(specification):
            primary = self._compile_view(specification)
            if not attention: return primary
            # Attention keeps the absolute word clock; clearing an old caption
            # must not postpone it into the second half of the transition.
            group = AnimationGroup(primary, *(self._compile_view(a) for a in attention), run_time=run_time)
            group._view_compiled = True
            return group
        incoming = getattr(self, '_incoming_handoff', None)
        if incoming is not None:
            self._incoming_handoff = None
            program = Then(Retire(incoming, run_time=run_time*.45),
                           Together(*operations, run_time=run_time*.55), run_time=run_time)
            return compiled(program)
        if clear_first:
            exits = [a for a in operations if isinstance(a, FadeOut) or (
                isinstance(a, AnimationGroup) and a.animations and all(isinstance(c, FadeOut) for c in a.animations))]
            rest = [a for a in operations if a not in exits]
            if exits and rest:
                return compiled(Then(Together(*exits), Together(*rest), run_time=run_time))
        if force_runtime:
            # Scene.play(..., run_time=t) applies t to each top-level animation,
            # not just an envelope around their original unequal durations.
            # Preserve that contract; explicit nested phases keep their ratios.
            for operation in operations:
                operation.set_run_time(run_time)
        return compiled(Together(*operations, run_time=run_time))

    def view_on_cue(self, name, *operations, run_time, reason, edge='start', clear_first=False):
        self._discover_attention(operations)
        previous_drawing = getattr(self, '_view_transition_active', False)
        self._view_transition_active = False
        try:
            anchor = self.wait_for_word(name, edge=edge)
        finally:
            self._view_transition_active = previous_drawing
        attention = self._attention_programs(name, operations, run_time, edge)
        program = self._view_program(operations, run_time, clear_first=clear_first, attention=attention)
        self._view_transition_active = True
        try:
            return self._play_aligned_word(name, anchor, program, run_time=run_time, reason=reason, edge=edge)
        finally:
            self._view_transition_active = previous_drawing

    def transition_view_on_cue(self, name, *operations, run_time, reason, edge='start'):
        return self.view_on_cue(name, *operations, run_time=run_time, reason=reason,
                                edge=edge, clear_first=True)

    def open_view(self, *operations, run_time, reason):
        attention = ()
        if self.narration is not None:
            attention = self._attention_programs(None, operations, run_time, 'start',
                          start_override=self.narration.elapsed(self))
        program = self._view_program(operations, run_time, attention=attention)
        self._view_transition_active = True
        try:
            return super().play_opening(program, run_time=run_time, reason=reason)
        finally:
            self._view_transition_active = False

    def animate_view(self, *operations, **kwargs):
        duration = kwargs.get('run_time', max((getattr(a, 'run_time', 1) for a in operations), default=1))
        attention = ()
        if self.narration is not None:
            attention = self._attention_programs(None, operations, duration, 'start',
                          start_override=self.narration.elapsed(self))
        program = self._view_program(operations, duration, attention=attention,
                                     force_runtime='run_time' in kwargs)
        self._view_transition_active = True
        try:
            return super().play(program, **kwargs)
        finally:
            self._view_transition_active = False

    def play(self, *operations, **kwargs):
        if getattr(self, '_view_transition_active', False):
            # Shared helpers can append a focus release after cue compilation.
            # Compile those additions too; no lifecycle operation escapes into
            # a second, procedural scene path.
            operations = tuple(a if getattr(a, '_view_compiled', False) or isinstance(a, Wait)
                               else self._compile_view(a) for a in operations)
            return super().play(*operations, **kwargs)
        if all(isinstance(a, Wait) for a in operations):
            return super().play(*operations, **kwargs)
        return self.animate_view(*operations, **kwargs)

    def wait(self, duration=1, *args, **kwargs):
        if self._attention_waiting or getattr(self, '_view_transition_active', False) or self.narration is None:
            return super().wait(duration, *args, **kwargs)
        self._discover_attention()
        end = self.narration.elapsed(self)+duration
        pending = sorted(((self.narration.word_anchor(binding.cue)['start'], binding)
                         for binding in self._word_attention if not binding.fired), key=lambda item:item[0])
        self._attention_waiting = True
        try:
            for time, binding in pending:
                now = self.narration.elapsed(self)
                if time < now-.001 or time >= end-.001 or binding.fired: continue
                if time+binding.duration > end+.001:
                    raise ValueError(f'Attention {binding.cue!r} overlaps the next cue; shorten its duration')
                if time > now: super().wait(time-now)
                self.view_on_cue(binding.cue, run_time=binding.duration,
                                  reason=binding.reason)
            remaining = end-self.narration.elapsed(self)
            if remaining > .001: return super().wait(remaining, *args, **kwargs)
        finally:
            self._attention_waiting = False

    # Shared proof/definition helpers also enter the view compiler. They cannot
    # accidentally reopen a procedural scene path after the source migration.
    def play_on_cue(self, *args, **kwargs):
        return self.view_on_cue(*args, **kwargs)

    def play_opening(self, *args, **kwargs):
        return self.open_view(*args, **kwargs)

    def transition_on_cue(self, *args, **kwargs):
        return self.transition_view_on_cue(*args, **kwargs)

    def _write_review_manifest(self):
        super()._write_review_manifest()
        if self._review_manifest_path:
            import json
            from pathlib import Path
            path = Path(self._review_manifest_path)
            document = json.loads(path.read_text(encoding='utf-8'))
            document['viewInfrastructure'] = {'schema': 1, 'groups': 'layout_containers',
                                               'steps': self._view_steps}
            temporary = path.with_suffix(path.suffix+'.view.tmp')
            temporary.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')
            temporary.replace(path)


from .presentation import SlideScene


class ViewScene(ViewSceneMixin, SlideScene):
    """A ready-to-use scene with layout views, word bindings and view timelines."""
