from manim import *


class Pulse(ApplyMethod):
    """A small scale-only attention cue that preserves every semantic color."""
    def __init__(self, mobject, scale_factor=1.04, **kwargs):
        kwargs.setdefault("rate_func", there_and_back)
        super().__init__(mobject.scale, scale_factor, **kwargs)


class ReplaceContent(Succession):
    """Replace a whole caption or composition without superimposing its text.

    Use Transform/ApplyDefinition for mathematical substitutions that preserve
    a student's visual reference. Use this for a different sentence or layout.
    """
    def __init__(self, source, target, **kwargs):
        super().__init__(FadeOut(source), FadeIn(target), **kwargs)

class FocusBox(SurroundingRectangle):
    """
    A dynamic SurroundingRectangle that can be moved or split.
    """
    def __init__(self, target, color=YELLOW, buff=0.1, **kwargs):
        super().__init__(target, color=color, buff=buff, **kwargs)
        self.target = target

    def move_to_target(self, new_target, **kwargs):
        """Returns a Transform animation to a new target"""
        self.target = new_target
        return self.animate.become(SurroundingRectangle(new_target, color=self.color, buff=self.buff, **self.kwargs))

    def split(self, *targets, **kwargs):
        """
        Returns an AnimationGroup that splits this FocusBox into multiple new FocusBoxes.
        """
        new_boxes = VGroup(*[FocusBox(t, color=self.color, buff=self.buff, **self.kwargs) for t in targets])
        return ReplacementTransform(self, new_boxes)

class Highlight(Animation):
    """
    A simple pulsing highlight animation.
    """
    def __init__(self, mobject, color=YELLOW, scale_factor=1.2, **kwargs):
        self.color = color
        self.scale_factor = scale_factor
        super().__init__(mobject, **kwargs)

    def interpolate_mobject(self, alpha):
        # Pulsing effect: 1.0 -> scale_factor -> 1.0
        val = 1 + (self.scale_factor - 1) * np.sin(PI * alpha)
        self.mobject.set_color(interpolate_color(self.mobject.get_color(), self.color, alpha))
        self.mobject.scale(val / self.last_val if hasattr(self, 'last_val') else val)
        self.last_val = val
