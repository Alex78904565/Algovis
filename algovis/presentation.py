"""Presentation primitives for authoring educational Manim videos."""

from dataclasses import dataclass
import inspect
import json
import numpy as np
import os
import time
from pathlib import Path

from manim import (
    AnimationGroup, Arrow, Circumscribe, DOWN, FadeIn, FadeOut, GrowArrow, Group,
    Indicate, MathTex, ORIGIN, RoundedRectangle, Succession, Text, UP, VGroup,
    Wait, config, TransformFromCopy,
)

from .theme import DEFAULT_SPACING, DEFAULT_THEME
from .narration import NarrationTrack
from .core.math import ApplyDefinition
from .review.inspection import capture_snapshot, semantic_objects, measured_font_size
from .utils.effects import Pulse


@dataclass(frozen=True)
class SlideRegion:
    """A named rectangular safe area within the camera frame."""

    center: tuple[float, float, float]
    width: float
    height: float

    def split_columns(self, *weights, gutter=DEFAULT_SPACING.section):
        """Return nested regions without changing or fitting any scene objects."""
        if not weights or any(not np.isfinite(w) or w <= 0 for w in weights):
            raise ValueError("Column weights must be positive")
        available = self.width-gutter*(len(weights)-1)
        if gutter < 0 or available <= 0:
            raise ValueError("Column gutters leave no content area")
        x = self.center[0]-self.width/2
        regions = []
        for weight in weights:
            width = available*weight/sum(weights)
            regions.append(SlideRegion((x+width/2,self.center[1],self.center[2]),width,self.height))
            x += width+gutter
        return tuple(regions)

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
        if self.theme.text_font:
            Text.set_default(font=self.theme.text_font)
        self.theme.apply(self)
        self.slide_layout = self.slide_layout or SlideLayout()
        self.current_slide = None
        self.narration = None
        self._review_manifest_path = os.environ.get("ALGOVIS_REVIEW_MANIFEST")
        self._review_snapshots = []
        self._review_animations = []
        self._review_plays = []
        self._review_initial_labels = {}
        self._review_object_ids = {}
        self._review_next_object_id = 1
        self._review_compiled_animations = None
        self._review_is_compiling_play = False

    def tear_down(self):
        try:
            self._write_review_manifest()
            super().tear_down()
        finally:
            if self.theme.text_font:
                Text.set_default()

    def play(self, *animations, **kwargs):
        animations = self._filter_cleanup_animations(animations)
        if not animations:
            # Repeated cleanup is a timed no-op, not an invitation to add an
            # absent object back to the scene. Keep narration timing intact.
            return self.wait(kwargs.get("run_time", 1.0))
        start = float(self.renderer.time)
        reviewing = bool(getattr(self, "_review_manifest_path", None))
        before = None
        if reviewing:
            self._capture_review_snapshot()
            before = self._review_snapshots[-1]
            frame = inspect.currentframe().f_back
            library = Path(__file__).resolve().parent
            while frame is not None:
                filename = Path(frame.f_code.co_filename).resolve()
                if filename.suffix == ".py" and not filename.is_relative_to(library):
                    try:
                        filename = filename.relative_to(Path.cwd())
                    except ValueError:
                        filename = Path(filename.name)
                    self._review_callsite = {"file": str(filename), "line": frame.f_lineno,
                                             "method": frame.f_code.co_name}
                    break
                frame = frame.f_back
            del frame
        self._review_compiled_animations = None
        self._review_is_compiling_play = bool(self._review_manifest_path)
        try:
            result = super().play(*animations, **kwargs)
        finally:
            self._review_is_compiling_play = False
        end = float(self.renderer.time)
        if reviewing:
            self._refresh_review_labels(self._review_compiled_animations or ())
        self._capture_review_snapshot()
        self._capture_review_animations(
            self._review_compiled_animations or (), start, end,
        )
        if reviewing:
            self._review_plays.append({
                "start": start, "end": end,
                "source": getattr(self, "_review_callsite", {}),
                "before": semantic_objects(before),
                "after": semantic_objects(self._review_snapshots[-1]),
                **getattr(self, "_review_active_cue", {}),
            })
        return result

    @staticmethod
    def _refresh_review_labels(animations):
        """Keep selection/audit text current when Transform reuses old objects.

        Manim moves the geometry but retains a MathTex source's tex_string.
        Preserve source labels separately for event records, while updating
        review-only semantic labels to describe what the viewer now sees.
        """
        def update(source, destination, inherited_size=None):
            # Transform changes geometry but keeps the source's initial SVG
            # height. Recalibrate the review-only font reference to the target
            # so a new fraction is not mistaken for a larger font.
            if getattr(source, "_algovis_typography_group", None):
                size = measured_font_size(destination)
                size = inherited_size if size is None else size
                if isinstance(size, (int,float)) and np.isfinite(size):
                    source._algovis_font_reference = (float(size),float(source.height))
                source._algovis_font_container = any(
                    isinstance(getattr(child,"tex_string",None),str) for child in destination.submobjects)
            else:
                size = measured_font_size(destination)
                size = inherited_size if size is None else size
            for attribute in ("_algovis_label", "text", "tex_string"):
                label = getattr(destination, attribute, None)
                if isinstance(label, str) and label.strip():
                    source._algovis_label = label
                    break
            for old, new in zip(source.submobjects, destination.submobjects):
                update(old, new, size)
        for animation in animations:
            # TransformFromCopy internally reverses source/destination and
            # runs the interpolation backwards. Its visible destination keeps
            # its own text and font; copying the source metadata would lie.
            if isinstance(animation, TransformFromCopy):
                continue
            rate_func = getattr(animation,"rate_func",None)
            if rate_func is not None and abs(float(rate_func(1))) < 1e-7:
                # Indicate and other there-and-back effects finish at their
                # original geometry, not at the enlarged focus target.
                continue
            destination = getattr(animation, "target_mobject", None)
            source = getattr(animation, "mobject", None)
            if source is not None and destination is not None:
                update(source, destination)
            for child in getattr(animation, "animations", ()):
                SlideScene._refresh_review_labels((child,))

    def compile_animations(self, *args, **kwargs):
        compiled = super().compile_animations(*args, **kwargs)
        if self._review_is_compiling_play:
            self._review_compiled_animations = list(compiled)
            def remember(animation):
                mob = getattr(animation, "mobject", None)
                target = getattr(animation, "target_mobject", None)
                self._review_initial_labels[id(animation)] = {
                    "fromLabel": self._review_object_label(mob) if mob is not None else "",
                    "toLabel": self._review_object_label(target) if target is not None else "",
                }
                for child in getattr(animation, "animations", ()):
                    remember(child)
            for animation in compiled:
                remember(animation)
        return compiled

    def wait(self, duration=1, *args, **kwargs):
        result = super().wait(duration, *args, **kwargs)
        self._capture_review_snapshot()
        return result

    def _capture_review_snapshot(self):
        """Capture selectable Manim objects for the local review surface.

        This does nothing during ordinary renders. The review server supplies
        ``ALGOVIS_REVIEW_MANIFEST`` only for an annotated section render.
        """
        if not self._review_manifest_path:
            return
        snapshot = capture_snapshot(self, float(config.frame_width),
                                    float(config.frame_height))
        if (
            self._review_snapshots
            and abs(self._review_snapshots[-1]["time"] - snapshot["time"]) < 1e-6
        ):
            self._review_snapshots[-1] = snapshot
        else:
            self._review_snapshots.append(snapshot)

    def _capture_review_animations(self, animations, start, end):
        """Record the real time span of every leaf animation in ``play``.

        A single Manim ``play`` call may contain several simultaneous
        animations, and animation groups may contain delayed children.  The
        review UI uses these intervals to draw stacked duration bars over the
        transcript instead of treating a narration phrase as a duration.
        """
        if not self._review_manifest_path or end <= start or not animations:
            return
        maximum = max(
            (float(getattr(animation, "run_time", 0.0)) for animation in animations),
            default=0.0,
        )
        scale = (end - start) / maximum if maximum > 0 else 1.0
        play_index = len({item["play"] for item in self._review_animations})
        for animation_index, animation in enumerate(animations):
            duration = min(
                end - start,
                max(0.0, float(getattr(animation, "run_time", end - start)) * scale),
            )
            self._append_review_animation(
                animation,
                start,
                start + duration,
                play_index,
                str(animation_index + 1),
            )

    def _append_review_animation(self, animation, start, end, play_index, path):
        focus_target = getattr(animation, "_algovis_focus_target", None)
        if focus_target is not None:
            self._review_animations.append({
                "id": f"play-{play_index + 1:04d}-{path}", "play": play_index,
                "kind": type(animation).__name__,
                "label": self._review_object_label(focus_target),
                "objectId": self._review_object_ids.get(id(focus_target)),
                "attention": getattr(animation, "_algovis_attention", None),
                "start": float(start), "end": float(end),
                "source": getattr(self, "_review_callsite", {}),
                **getattr(self, "_review_active_cue", {}),
            })
            return
        if isinstance(animation, ApplyDefinition):
            source = self._review_object_label(animation.definition)
            destination = self._review_object_label(animation.result)
            self._review_animations.append({
                "id": f"play-{play_index + 1:04d}-{path}",
                "play": play_index,
                "kind": "ApplyDefinition",
                "label": f"Apply definition: {source} → {destination}",
                "objectId": self._review_object_ids.get(id(animation.result)),
                "sourceObjectId": self._review_object_ids.get(id(animation.definition)),
                "start": float(start), "end": float(end),
                "source": getattr(self, "_review_callsite", {}),
                **getattr(self, "_review_active_cue", {}),
            })
            return
        children = getattr(animation, "anims_with_timings", None)
        if children is not None and len(children):
            local_duration = max(
                (float(timing["end"]) for timing in children),
                default=float(getattr(animation, "run_time", 0.0)),
            )
            scale = (end - start) / local_duration if local_duration > 0 else 1.0
            for child_index, timing in enumerate(children):
                self._append_review_animation(
                    timing["anim"],
                    start + float(timing["start"]) * scale,
                    start + float(timing["end"]) * scale,
                    play_index,
                    f"{path}.{child_index + 1}",
                )
            return

        if isinstance(animation, Wait):
            return

        mobject = getattr(animation, "mobject", None)
        target = getattr(animation, "target_mobject", None)
        initial = getattr(self, "_review_initial_labels", {}).get(id(animation), {})
        label = initial.get("fromLabel") or (self._review_object_label(mobject) if mobject is not None else "")
        target_label = (
            self._review_object_label(target) if target is not None else ""
        )
        if target_label and target_label != label:
            label = f"{label} → {target_label}" if label else target_label
        object_id = (
            self._review_object_ids.get(id(mobject)) if mobject is not None else None
        )
        self._review_animations.append({
            "id": f"play-{play_index + 1:04d}-{path}",
            "play": play_index,
            "kind": type(animation).__name__.lstrip("_"),
            "label": label or type(animation).__name__.lstrip("_"),
            "fromLabel": initial.get("fromLabel", label),
            "toLabel": initial.get("toLabel", target_label),
            "attention": getattr(animation, "_algovis_attention", None),
            "source": getattr(self, "_review_callsite", {}),
            "objectId": object_id,
            "start": float(start),
            "end": float(end),
            **getattr(self, "_review_active_cue", {}),
        })

    @staticmethod
    def _review_object_label(mobject):
        for attribute in ("_algovis_label", "text", "tex_string"):
            value = getattr(mobject, attribute, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
        labels = []
        for descendant in mobject.get_family()[1:]:
            for attribute in ("_algovis_label", "text", "tex_string"):
                value = getattr(descendant, attribute, None)
                if isinstance(value, str) and value.strip():
                    cleaned = value.strip()
                    if cleaned not in labels:
                        labels.append(cleaned)
                    break
            if len(labels) >= 3:
                break
        return " · ".join(labels) or type(mobject).__name__

    def _write_review_manifest(self):
        if not self._review_manifest_path:
            return
        self._capture_review_snapshot()
        path = Path(self._review_manifest_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({
                "scene": type(self).__name__,
                "frameRate": float(config.frame_rate),
                "frame": {
                    "width": float(config.frame_width),
                    "height": float(config.frame_height),
                },
                "snapshots": self._review_snapshots,
                "animations": self._review_animations,
                "plays": self._review_plays,
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        # A Windows viewer or indexer can briefly hold the old manifest open.
        # Retry the atomic replacement; never truncate the last usable file.
        for attempt in range(4):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 3:
                    raise
                time.sleep(0.05 * 2 ** attempt)

    def begin_narration(self, cue_path, *, project_root=None, gain=None):
        """Attach a mastered voice track and return its named cue timeline."""
        self.narration = NarrationTrack.from_json(cue_path, project_root=project_root)
        return self.narration.start(self, gain=gain)

    def wait_for_cue(self, name, offset=0.0):
        if self.narration is None:
            raise RuntimeError("Call begin_narration() before wait_for_cue().")
        result = self.narration.wait_for(self, name, offset=offset)
        self._review_active_cue = {
            "cue": name, "cueTime": self.narration.cue_time(name),
            "cueOffset": float(offset),
        }
        return result

    def play_to_cue(self, name, *animations, minimum=0.05, offset=0.0):
        if self.narration is None:
            raise RuntimeError("Call begin_narration() before play_to_cue().")
        return self.narration.play_until(
            self, name, *animations, minimum=minimum, offset=offset,
        )

    def play_on_cue(self, name, *animations, run_time, reason):
        """Schedule one content change on verified words, or fail the render.

        Unlike a separate wait/play pair, this operation cannot inherit an
        unrelated cue or silently arrive after another animation used its time.
        Supply ``transcriptWords`` in the narration document. Cue times select
        the occurrence; the recording's word timestamps determine the start.
        """
        if self.narration is None:
            raise RuntimeError("Call begin_narration() before play_on_cue().")
        if not str(reason).strip():
            raise ValueError("A word-timed content change needs an instructional reason")
        anchor = self.narration.wait_for_word(self, name)
        self._review_active_cue = {
            "cue": name, "cueTime": anchor["start"], "cueOffset": 0.0,
            "wordTiming": {"trigger": self.narration.cues[name].phrase,
                           "time": anchor["start"], "reason": str(reason),
                           "narrationStart": self.narration.start_time},
        }
        try:
            return self.play(*animations, run_time=float(run_time))
        finally:
            # A later play cannot inherit this operation's strict declaration.
            self._review_active_cue.pop("wordTiming", None)

    def spoken_focus(self, target, kind="object", *, source=None, color=None,
                     scale_factor=1.04, buff=0.08, arrow_hold=0.18,
                     trigger=None, reason=None):
        """Return a restrained attention cue for the currently spoken idea.

        ``object`` pulses an already isolated object. ``term`` boxes one part
        of a larger expression. ``relationship`` briefly grows a directional
        arrow from ``source`` to ``target``.
        """
        # Spoken attention should not silently turn an object into an
        # operation, success, or error. Blue is the neutral "look here" role.
        color = color or self.theme.role_color("current")
        if kind == "object":
            return Pulse(target, scale_factor=scale_factor, trigger=trigger, reason=reason)
        if kind == "term":
            animation = Circumscribe(target, color=color, buff=buff, fade_out=True)
            animation._algovis_attention = {"trigger": trigger, "reason": reason}
            animation._algovis_focus_target = target
            return animation
        if kind == "relationship":
            if source is None:
                raise ValueError("A relationship focus requires source=...")
            delta = target.get_center() - source.get_center()
            norm = np.linalg.norm(delta)
            direction = delta / norm if norm > 1e-6 else np.array((1.0, 0.0, 0.0))
            arrow = Arrow(
                source.get_boundary_point(direction),
                target.get_boundary_point(-direction),
                buff=buff,
                color=color,
                stroke_width=2.4,
                max_tip_length_to_length_ratio=0.18,
            )
            return Succession(
                GrowArrow(arrow), Wait(arrow_hold), FadeOut(arrow),
            )
        raise ValueError(f"Unknown spoken-focus kind: {kind!r}")

    def finish_narration(self, tail=0.0):
        if self.narration is None:
            raise RuntimeError("Call begin_narration() before finish_narration().")
        return self.narration.finish(self, tail=tail)

    def make_slide(self, title, kicker=None):
        return Slide(title, kicker, theme=self.theme, layout=self.slide_layout)

    def transition(self, *animations, **kwargs):
        """Clear outgoing material before revealing its replacement.

        Use for two compositions occupying the same space. The supplied
        runtime covers both phases, so narration cues do not move.
        """
        animations = self._filter_cleanup_animations(animations)
        def only_exits(animation):
            if isinstance(animation, FadeOut):
                return True
            # wipe() returns a group of fades. Treat the whole exit as an
            # exit, while preserving timing inside authored mixed sequences.
            if isinstance(animation, AnimationGroup):
                return bool(animation.animations) and all(
                    only_exits(child) for child in animation.animations
                )
            return False

        outgoing = [animation for animation in animations if only_exits(animation)]
        incoming = [animation for animation in animations if not only_exits(animation)]
        if not outgoing or not incoming:
            return self.play(*animations, **kwargs)
        return self.play(Succession(
            AnimationGroup(*outgoing, lag_ratio=0),
            AnimationGroup(*incoming, lag_ratio=0),
        ), **kwargs)

    def _filter_cleanup_animations(self, animations):
        """Prune absent children from direct cleanup requests before Manim adds them.

        Do not descend into a Succession: its later cleanup may target an
        object introduced by an earlier step in that same sequence.
        """
        result = []
        for animation in animations:
            if isinstance(animation, FadeOut):
                present = self.present_mobjects(animation.mobject)
                if not present:
                    continue
                if present != (animation.mobject,):
                    animation.mobject = present[0] if len(present) == 1 else Group(*present)
            result.append(animation)
        return tuple(result)

    def begin_slide(self, title, kicker=None, *, transition=True):
        incoming = self.make_slide(title, kicker)
        if transition and self.current_slide is not None:
            outgoing = self.present_mobjects(*self.current_slide.mobjects)
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
            self.transition(*animations, run_time=self.default_transition_time)
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
            present = self.present_mobjects(*objects)
            if present:
                self.play(*[FadeOut(m, shift=DOWN * 0.06) for m in present],
                          run_time=run_time or self.default_transition_time)

    # Compatibility helpers make gradual migration of existing scenes easy.
    def title(self, text, kicker):
        return self.make_slide(text, kicker).header

    def present_mobjects(self, *mobjects):
        """Return only requested mobjects that are actually in the scene.

        Fading an absent mobject can make Manim add it for the animation and
        create the exact pop-in we are trying to avoid. This identity-based
        filter also makes repeated cleanup calls harmless. A temporary wrapper
        may no longer be a scene root after its children were animated; in
        that case return its actually present descendants instead.
        """
        visible_ids = {
            id(member)
            for root in self.mobjects
            for member in root.get_family()
        }
        candidates = []
        selected = set()

        def collect(mobject):
            if id(mobject) in selected:
                return
            if id(mobject) in visible_ids:
                candidates.append(mobject)
                selected.add(id(mobject))
                return
            for child in mobject.submobjects:
                collect(child)

        for mobject in mobjects:
            collect(mobject)
        # A caller may request both a parent and one of its children. Animate
        # the parent once, regardless of which was supplied first.
        covered = {
            id(member)
            for candidate in candidates
            for member in candidate.get_family()[1:]
        }
        return tuple(candidate for candidate in candidates
                     if id(candidate) not in covered)

    def wipe(self, *mobjects):
        present = self.present_mobjects(*mobjects)
        if not present:
            return Wait(0)
        return AnimationGroup(*[FadeOut(m, shift=DOWN * 0.12)
                                for m in present], lag_ratio=0.04)

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
