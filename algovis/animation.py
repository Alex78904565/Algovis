"""A lesson animation schedules declarative scenes and component actions."""
from dataclasses import dataclass,replace
import math


@dataclass(frozen=True)
class SceneBeat:
    scene: object
    cue: str | None
    duration: float
    reason: str
    edge: str = 'start'


@dataclass(frozen=True)
class ActionBeat:
    factory: object
    cue: str | None
    duration: float
    reason: str
    edge: str = 'start'


@dataclass(frozen=True)
class SceneGroupBeat:
    group: object


class LessonAnimation:
    """Plan scene states; the renderer owns execution and the narration clock.

    Same object: retain/move it. ``object.copy()``: carry a duplicate. Objects
    omitted from the next scene retire automatically. Actions are for intrinsic
    component processes such as drawing a tree layer or populating an array.
    Factories run on their cue, after prior scene layouts have been installed.
    """
    def __init__(self):
        self.beats=[]
        self._played=0
        self._last_cue=None
        self._last_scene=None
        self._intrinsic_since_scene=False

    @staticmethod
    def _check(duration,reason):
        if not math.isfinite(duration) or duration<=0 or not str(reason).strip():
            raise ValueError('An animation beat needs a positive duration and an instructional reason')

    def add(self, scene, *, on=None, duration=.6, reason, edge='start'):
        self._check(duration,reason)
        if edge not in ('start','end'):raise ValueError('Cue edge must be start or end')
        # Freeze layout plans, while preserving the live object identities.
        self.beats.append(SceneBeat(scene.snapshot(),on,float(duration),reason,edge))
        return scene

    def action(self, factory, *, on=None, duration=.5, reason, edge='start'):
        self._check(duration,reason)
        if not callable(factory):raise TypeError('An action is a factory evaluated on its cue')
        if edge not in ('start','end'):raise ValueError('Cue edge must be start or end')
        self.beats.append(ActionBeat(factory,on,float(duration),reason,edge))
        return self

    def group(self,name):
        """Plan all steps of one explanation before choosing their shared fit."""
        group=SceneSequence(name)
        self.beats.append(SceneGroupBeat(group))
        return group

    def play(self, renderer):
        for beat in self.beats[self._played:]:
            if isinstance(beat,SceneGroupBeat):
                child=beat.group
                child._last_cue=self._last_cue
                child._last_scene=self._last_scene
                child._intrinsic_since_scene=self._intrinsic_since_scene
                child.play(renderer)
                self._last_cue=child._last_cue
                self._last_scene=child._last_scene
                self._intrinsic_since_scene=child._intrinsic_since_scene
                self._played+=1
                continue
            if isinstance(beat,SceneBeat):
                planned=beat.scene.snapshot()
                # Every composition change inherits completed component state,
                # including caption-only beats after the first regrouping.
                planned.retain_live_models(self._last_scene)
                if beat.cue is not None and beat.cue==self._last_cue:
                    renderer.transition_phase(beat.cue,planned,run_time=beat.duration,reason=beat.reason)
                else:
                    renderer.transition_to(planned,cue=beat.cue,run_time=beat.duration,
                                           reason=beat.reason,edge=beat.edge)
                self._last_scene=planned
                self._intrinsic_since_scene=False
            else:
                # Delay preparation too: future actions must not mutate a live
                # object or capture its old position before their spoken cue.
                from .view_timeline import Later
                operation=Later(beat.factory,run_time=beat.duration)
                if beat.cue is None:
                    renderer.open_view(operation,run_time=beat.duration,reason=beat.reason)
                elif beat.cue==self._last_cue:
                    renderer.play_phase(beat.cue,operation,run_time=beat.duration,reason=beat.reason)
                else:
                    renderer.view_on_cue(beat.cue,operation,run_time=beat.duration,
                                         reason=beat.reason,edge=beat.edge)
                self._intrinsic_since_scene=True
            self._last_cue=beat.cue
            self._played+=1
        # Future scene states have their own detached snapshots. Subsequent
        # authoring after playback should inherit the actual completed live
        # state, including intrinsic population and reveal processes.
        if self._last_scene is not None:
            for item in self._last_scene.items.values():
                item.object.__dict__.pop('_planned_model',None)
        return self


class SceneSequence(LessonAnimation):
    """An explanation-sized layout scope, e.g. every step of one proof.

    Add all scene states, then play. The complete sequence chooses one fit and
    shared row reservations before its first frame. Appending later would make
    the already-rendered layout unknowable, so a played sequence is sealed.
    """
    def __init__(self,name):
        super().__init__()
        if not str(name).strip():raise ValueError('A scene sequence needs a descriptive name')
        self.name=str(name)
        self._sealed=False
        self.layout_report=None

    def _open(self):
        if self._sealed:raise ValueError('This scene sequence is already planned; add every step before playback')

    def add(self,*args,**kwargs):
        self._open();return super().add(*args,**kwargs)

    def action(self,*args,**kwargs):
        self._open();return super().action(*args,**kwargs)

    def group(self,*args,**kwargs):
        self._open();return super().group(*args,**kwargs)

    def _scene_slots(self):
        for index,beat in enumerate(self.beats):
            if isinstance(beat,SceneBeat):yield self,index,beat
            elif isinstance(beat,SceneGroupBeat):yield from beat.group._scene_slots()

    def compile(self):
        if self._sealed:return self
        from .sequence_layout import plan_sequence
        slots=list(self._scene_slots())
        views,report=plan_sequence(self.name,[beat.scene for _,_,beat in slots],previous=self._last_scene)
        for (owner,index,beat),view in zip(slots,views):
            owner.beats[index]=replace(beat,scene=view)
            owner.layout_report=report
        def seal(group):
            group._sealed=True
            for beat in group.beats:
                if isinstance(beat,SceneGroupBeat):seal(beat.group)
        self.layout_report=report
        seal(self)
        return self

    def play(self,renderer):
        self.compile()
        return super().play(renderer)
