"""Presentation primitives for authoring educational Manim videos."""

from dataclasses import dataclass

from manim import (
    AnimationGroup, DOWN, FadeIn, FadeOut, MathTex, ORIGIN, RoundedRectangle,
    Text, UP, VGroup, config,
)

from .theme import DEFAULT_SPACING, DEFAULT_THEME
from .narration import NarrationTrack


@dataclass(frozen=True)
class SlideRegion:
    """A named rectangular safe area within the camera frame."""

    center: tuple[float, float, float]
    width: float
    height: float

    def place(self, mobject, padding=0.0, allow_upscale=False):
        """Fit and center ``mobject`` inside this region."""
        available_width = max(0.01, self.width - 2 * padding)
        available_height = max(0.01, self.height - 2 * padding)
        factor = min(available_width / max(mobject.width, 0.001),
                     available_height / max(mobject.height, 0.001))
        if allow_upscale or factor < 1:
            mobject.scale(factor)
        return mobject.move_to(self.center)


class SlideLayout:
    """Frame-relative title, body, footer, and split-panel safe areas."""

    def __init__(self, margin=0.28, header_height=1.05, footer_height=0.68,
                 gutter=0.34):
        width = float(config.frame_width)
        height = float(config.frame_height)
        body_height = height - 2 * margin - header_height - footer_height
        body_y = (footer_height - header_height) / 2
        body_width = width - 2 * margin
        half_width = (body_width - gutter) / 2
        self.header = SlideRegion(
            (0, height / 2 - margin - header_height / 2, 0),
            body_width, header_height,
        )
        self.body = SlideRegion((0, body_y, 0), body_width, body_height)
        self.footer = SlideRegion(
            (0, -height / 2 + margin + footer_height / 2, 0),
            body_width, footer_height,
        )
        offset = (half_width + gutter) / 2
        self.left = SlideRegion((-offset, body_y, 0), half_width, body_height)
        self.right = SlideRegion((offset, body_y, 0), half_width, body_height)

    def region(self, name):
        try:
            return getattr(self, name)
        except AttributeError as exc:
            raise ValueError(f"Unknown slide region: {name!r}") from exc


class Slide:
    """Content and lifecycle state for one visual beat.

    A Slide intentionally does not add one giant parent VGroup to the scene.
    Manim can reorder nested children when they are animated independently;
    tracking the drawable objects separately avoids those lifecycle glitches.
    """

    def __init__(self, title, kicker=None, *, theme=DEFAULT_THEME, layout=None):
        self.theme = theme
        self.layout = layout or SlideLayout()
        heading = Text(title, font_size=38, weight="BOLD", color=theme.primary)
        if kicker:
            eyebrow = Text(str(kicker).upper(), font_size=15, color=theme.muted)
            self.header = VGroup(eyebrow, heading).arrange(
                DOWN, buff=DEFAULT_SPACING.tight,
            )
        else:
            self.header = VGroup(heading)
        self.layout.header.place(self.header, padding=0.04)
        self.content = []
        self.footer = None

    @property
    def mobjects(self):
        objects = [self.header, *self.content]
        if self.footer is not None:
            objects.append(self.footer)
        return objects

    def place(self, mobject, region="body", *, padding=0.12,
              allow_upscale=False, track=True):
        self.layout.region(region).place(mobject, padding, allow_upscale)
        if track and mobject not in self.content:
            self.content.append(mobject)
        return mobject

    def stack(self, *mobjects, region="body", direction=DOWN,
              buff=DEFAULT_SPACING.normal,
              aligned_edge=None, padding=0.12):
        group = VGroup(*mobjects)
        kwargs = {"buff": buff}
        if aligned_edge is not None:
            kwargs["aligned_edge"] = aligned_edge
        group.arrange(direction, **kwargs)
        return self.place(group, region, padding=padding)

    def set_caption(self, text_or_mobject, *, color=None, font_size=22):
        caption = (
            Text(text_or_mobject, font_size=font_size,
                 color=color or self.theme.muted)
            if isinstance(text_or_mobject, str)
            else text_or_mobject
        )
        self.layout.footer.place(caption, padding=0.04)
        self.footer = caption
        return caption


class SlideSceneMixin:
    """Author-facing slide lifecycle mixed into a Manim ``Scene`` subclass."""

    theme = DEFAULT_THEME
    slide_layout = None
    default_transition_time = 0.55

    def setup(self):
        super().setup()
        self.theme.apply(self)
        self.slide_layout = self.slide_layout or SlideLayout()
        self.current_slide = None
        self.narration = None

    def begin_narration(self, cue_path, *, project_root=None, gain=None):
        """Attach a mastered voice track and return its named cue timeline."""
        self.narration = NarrationTrack.from_json(cue_path, project_root=project_root)
        return self.narration.start(self, gain=gain)

    def wait_for_cue(self, name, offset=0.0):
        if self.narration is None:
            raise RuntimeError("Call begin_narration() before wait_for_cue().")
        return self.narration.wait_for(self, name, offset=offset)

    def play_to_cue(self, name, *animations, minimum=0.05, offset=0.0):
        if self.narration is None:
            raise RuntimeError("Call begin_narration() before play_to_cue().")
        return self.narration.play_until(
            self, name, *animations, minimum=minimum, offset=offset,
        )

    def finish_narration(self, tail=0.0):
        if self.narration is None:
            raise RuntimeError("Call begin_narration() before finish_narration().")
        return self.narration.finish(self, tail=tail)

    def make_slide(self, title, kicker=None):
        return Slide(title, kicker, theme=self.theme, layout=self.slide_layout)

    def begin_slide(self, title, kicker=None, *, transition=True):
        incoming = self.make_slide(title, kicker)
        if transition and self.current_slide is not None:
            outgoing = list(self.current_slide.mobjects)
            self.play(AnimationGroup(*[FadeOut(m, shift=DOWN * 0.08)
                                       for m in outgoing], lag_ratio=0.03),
                      run_time=self.default_transition_time)
        self.current_slide = incoming
        self.play(FadeIn(incoming.header, shift=DOWN * 0.06),
                  run_time=self.default_transition_time)
        return incoming

    def show(self, mobject, *, region="body", animation=None, run_time=None,
             padding=0.12, allow_upscale=False):
        if self.current_slide is None:
            raise RuntimeError("Call begin_slide() before show().")
        self.current_slide.place(mobject, region, padding=padding,
                                 allow_upscale=allow_upscale)
        self.play(animation or FadeIn(mobject), **({} if run_time is None else {"run_time": run_time}))
        return mobject

    def caption(self, text, color=None, size=22, *, animate=True):
        if self.current_slide is None:
            # Also useful to legacy scenes that adopt the base incrementally.
            caption = Text(text, font_size=size, color=color or self.theme.muted)
            return self.slide_layout.footer.place(caption, padding=0.04)
        old_caption = self.current_slide.footer
        caption = self.current_slide.set_caption(text, color=color, font_size=size)
        if animate:
            animations = [FadeIn(caption, shift=UP * 0.05)]
            if old_caption is not None:
                animations.insert(0, FadeOut(old_caption, shift=UP * 0.05))
            self.play(*animations, run_time=self.default_transition_time)
        return caption

    def clear_content(self, *, keep_caption=False, run_time=None):
        if self.current_slide is None:
            return
        objects = list(self.current_slide.content)
        if not keep_caption and self.current_slide.footer is not None:
            objects.append(self.current_slide.footer)
            self.current_slide.footer = None
        self.current_slide.content.clear()
        if objects:
            self.play(*[FadeOut(m, shift=DOWN * 0.06) for m in objects],
                      run_time=run_time or self.default_transition_time)

    # Compatibility helpers make gradual migration of existing scenes easy.
    def title(self, text, kicker):
        return self.make_slide(text, kicker).header

    def wipe(self, *mobjects):
        return AnimationGroup(*[FadeOut(m, shift=DOWN * 0.12)
                                for m in mobjects], lag_ratio=0.04)

    def card(self, tex, color=None, scale=0.72):
        label = MathTex(tex, color=self.theme.foreground).scale(scale)
        box = RoundedRectangle(
            corner_radius=0.08,
            width=label.width + 0.38,
            height=label.height + 0.28,
            color=color or self.theme.primary,
            fill_color=self.theme.surface,
            fill_opacity=0.95,
        )
        return VGroup(box, label)


def slide_scene(base_scene):
    """Create a SlideScene base for unusual Manim Scene subclasses."""
    return type(f"Slide{base_scene.__name__}", (SlideSceneMixin, base_scene), {})


from manim import Scene  # Imported late to keep the mixin reusable.


class SlideScene(SlideSceneMixin, Scene):
    """Default themed scene with slide lifecycle and safe layout regions."""

    pass
