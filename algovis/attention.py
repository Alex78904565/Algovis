"""Object-level attention declarations, resolved against verified spoken words."""
from dataclasses import dataclass
import numpy as np
from manim import Circumscribe, Transform, there_and_back
from .utils.effects import Pulse


@dataclass
class WordAttention:
    target: object
    cue: str
    style: str = 'auto'
    reason: str = ''
    duration: float = .45
    callback: object = None
    fired: bool = False
    scale_factor: float = 1.04

    @property
    def artwork(self):
        from .composition import SlideObject
        return self.target.mobject if isinstance(self.target,SlideObject) else self.target

    def __deepcopy__(self, memo):
        # A binding belongs to its original object, not its visual copies.
        # In particular, never deep-copy a callback's scene or audio thread.
        return self

    def animation(self, scene):
        from .review.inspection import visible_opacity
        target=self.artwork
        present = {id(part) for part in scene.get_mobject_family_members()}
        if id(target) not in present and not any(id(p) in present for p in target.get_family()):
            raise ValueError(f'Attention target for {self.cue!r} is absent')
        label = getattr(target, 'label', target)
        if visible_opacity(label) <= .015:
            raise ValueError(f'Attention target for {self.cue!r} is not readable')
        painted = [part for part in label.get_family() if part.has_points() and visible_opacity(part)>.015]
        if any(id(part) not in present for part in painted):
            raise ValueError(f'Attention target for {self.cue!r} has glyphs that are not on screen')
        if self.callback is not None:
            return self.callback(scene, target)
        trigger = scene.narration.cues[self.cue].phrase
        style = self.style
        if style == 'auto':
            style = 'box' if getattr(target, '_view_attention_term', False) else 'pulse'
        if style in ('pulse', 'plus'):
            # 'plus' addresses an existing operation token. It never invents a
            # symbol or changes the mathematical expression being explained.
            return Pulse(target, trigger=trigger, reason=self.reason, scale_factor=self.scale_factor)
        if style == 'box':
            animation = Circumscribe(target, color=scene.theme.primary, buff=.06, fade_out=True)
            animation._algovis_attention = {'trigger':trigger, 'reason':self.reason}
            animation._algovis_focus_target = target
            return animation
        if style == 'fill':
            frame = getattr(target, 'box', None)
            if frame is None:
                raise ValueError('A fill attention binding needs a framed object; use box for equation terms')
            destination = frame.copy().set_fill(frame.get_stroke_color(), opacity=.25)
            animation = Transform(frame, destination, rate_func=there_and_back)
            animation._algovis_attention = {'trigger':trigger, 'reason':self.reason}
            return animation
        raise ValueError(f'Unknown attention style: {style!r}')


def attention_declaration(mobject, cue, *, style='auto', reason, duration=.45, callback=None, scale_factor=1.04):
    if not str(reason).strip() or not np.isfinite(duration) or duration <= 0:
        raise ValueError('Word attention needs a reason and positive finite duration')
    if style not in ('auto', 'pulse', 'box', 'fill', 'plus'):
        raise ValueError(f'Unknown attention style: {style!r}')
    return WordAttention(mobject, str(cue), style, str(reason), float(duration), callback,
                         scale_factor=float(scale_factor))
