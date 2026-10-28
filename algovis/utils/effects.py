from manim import *


class DeferredAnimation(Animation):
    """Build and activate an animation only when its sequence reaches it.

    Manim groups may introduce later Create/Transform targets during setup.
    Use a factory when those objects must remain absent until prerequisites
    have finished, e.g. ``Succession(fill_bases, DeferredAnimation(add_guide))``.
    The factory returns one animation (possibly an AnimationGroup).

    Also defer later substitutions and cancellation marks. A preconstructed
    Succession collects the sources of its future FadeOut/Transform steps;
    those sources can otherwise become visible while an earlier rule is being
    copied or held. Wrap each later phase, not just its initial reveal.
    """
    def __init__(self, factory, **kwargs):
        self.factory = factory
        self.animation = None
        self.scene = None
        self._inner_cleaned = False
        kwargs.setdefault("rate_func", linear)
        super().__init__(Group(), introducer=True, **kwargs)

    def _setup_scene(self, scene):
        self.scene = scene

    def begin(self):
        if self.scene is None:
            raise RuntimeError("DeferredAnimation must be set up with a scene before beginning")
        self._inner_cleaned = False
        self.animation = self.factory()
        self.scene.add_mobjects_from_animations([self.animation])
        self.animation._setup_scene(self.scene)
        self.animation.begin()
        super().begin()

    def interpolate_mobject(self, alpha):
        if self.animation is not None:
            self.animation.interpolate(alpha)

    def update_mobjects(self, dt):
        if self.animation is not None:
            self.animation.update_mobjects(dt)

    def finish(self):
        super().finish()
        self.animation.finish()
        # A following deferred factory may immediately animate this result.
        # Adopt copies and retire outgoing objects now, before that factory
        # starts; waiting for the enclosing group's cleanup paints both stages.
        self._clean_up_inner(self.scene)

    def _clean_up_inner(self, scene):
        if self._inner_cleaned:
            return
        self.animation.clean_up_from_scene(scene)
        scene.remove(self.mobject)
        self._inner_cleaned = True

    def clean_up_from_scene(self, scene):
        self._clean_up_inner(scene)


class Pulse(ApplyMethod):
    """A small scale-only attention cue that preserves every semantic color."""
    def __init__(self, mobject, scale_factor=1.04, *, trigger=None, reason=None, **kwargs):
        self._algovis_attention = {"trigger": trigger, "reason": reason}
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
