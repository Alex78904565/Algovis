"""A small, review-first language for cue-driven educational animation.

Storyboard files describe *why* the screen changes without exposing Manim
implementation details.  They are intentionally plain text so an instructor
can audit an entire lesson before any rendering work begins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import shlex


SEMANTIC_ROLES = {
    'good',        # Favorable evaluation; overrides status and attention roles.
    'bad',         # Unfavorable evaluation; overrides status and attention roles.
    "neutral",     # Ordinary structure or context.
    "current",     # The object currently named by the narration.
    "operation",   # A transformation, choice, or arithmetic operation.
    "retained",    # Computed, accepted, proved, or kept work.
    "repeated",    # Duplicate, rejected, impossible, or discarded work.
}

ATTENTION_STYLES = {"pulse", "box", "arrow", "tint", "none"}
ENTRY_STYLES = {"fade", "write", "draw", "grow", "none"}
EXIT_STYLES = {"fade", "shrink", "move", "none"}

ACTION_VERBS = {
    "show", "hide", "focus", "unfocus", "transform", "fill", "move",
    "merge", "retain", "clear", "change", "animate", "caption", "hold",
    "note", "together", "apply",
}


class StoryboardSyntaxError(ValueError):
    """Raised when a storyboard cannot be parsed or validated."""


@dataclass(frozen=True)
class StoryAction:
    verb: str
    args: tuple[str, ...] = ()
    options: tuple[tuple[str, str], ...] = ()
    children: tuple["StoryAction", ...] = ()
    line: int = field(default=0, compare=False)

    @property
    def option_map(self):
        return dict(self.options)

    def to_source(self, indent=2):
        prefix = " " * indent
        if self.verb == "together":
            lines = [f"{prefix}together:"]
            lines.extend(child.to_source(indent + 2) for child in self.children)
            return "\n".join(lines)
        def source_token(value):
            value = str(value)
            return json.dumps(value) if any(char.isspace() for char in value) else value

        tokens = [self.verb, *(source_token(arg) for arg in self.args)]
        tokens.extend(f"{key}={source_token(value)}" for key, value in self.options)
        return prefix + " ".join(tokens)


@dataclass(frozen=True)
class StoryBeat:
    cue: str
    offset: float = 0.0
    phrase: str = ""
    actions: tuple[StoryAction, ...] = ()
    line: int = field(default=0, compare=False)

    def to_source(self, *, indent=2, keyword="at"):
        offset = f" {self.offset:+g}" if self.offset else ""
        phrase = f" say {json.dumps(self.phrase)}" if self.phrase else ""
        prefix = " " * indent
        header = f"{prefix}{keyword} {self.cue}{offset}{phrase}:"
        if not self.actions:
            return header + "\n" + " " * (indent + 2) + "hold"
        return header + "\n" + "\n".join(
            action.to_source(indent + 2) for action in self.actions
        )


@dataclass(frozen=True)
class StoryObject:
    name: str
    kind: str
    description: str
    line: int = field(default=0, compare=False)

    def to_source(self):
        return f"object {self.name} {self.kind} {json.dumps(self.description)}"


@dataclass
class StoryAnimation:
    """One high-level visual idea made from phrase-triggered components."""

    name: str
    title: str
    goal: str = ""
    components: list[StoryBeat] = field(default_factory=list)
    line: int = field(default=0, compare=False)

    def to_source(self):
        lines = [f"animation {self.name} {json.dumps(self.title)}:"]
        if self.goal:
            lines.append(f"  goal {json.dumps(self.goal)}")
        for component in self.components:
            lines.append(component.to_source(indent=2, keyword="component"))
        return "\n".join(lines)

    @property
    def visual_change_count(self):
        return sum(_visual_action_count(beat.actions) for beat in self.components)


@dataclass
class Storyboard:
    section: str
    title: str
    audio: str = ""
    version: int = 2
    objects: dict[str, StoryObject] = field(default_factory=dict)
    animations: list[StoryAnimation] = field(default_factory=list)
    source_path: Path | None = None

    @property
    def beats(self):
        return [
            beat
            for animation in self.animations
            for beat in animation.components
        ]

    @classmethod
    def load(cls, path):
        path = Path(path)
        board = parse_storyboard(path.read_text(encoding="utf-8"))
        board.source_path = path
        return board

    def beat(self, cue):
        matches = [beat for beat in self.beats if beat.cue == cue]
        if not matches:
            raise KeyError(f"No storyboard beat named {cue!r}")
        if len(matches) > 1:
            raise KeyError(
                f"Cue {cue!r} has multiple beats; use beats_for(cue) instead"
            )
        return matches[0]

    def beats_for(self, cue):
        return tuple(beat for beat in self.beats if beat.cue == cue)

    def validate(self, cue_path=None, *, require_all_cues=False):
        errors = []
        if self.version not in {1, 2}:
            errors.append(f"Unsupported storyboard version {self.version}")
        if not self.section:
            errors.append("Missing section id")
        if not self.title:
            errors.append("Missing section title")

        animation_names = set()
        for animation in self.animations:
            if not animation.name:
                errors.append(f"Line {animation.line}: animation needs an id")
            if animation.name in animation_names:
                errors.append(
                    f"Line {animation.line}: duplicate animation id {animation.name!r}"
                )
            animation_names.add(animation.name)
            if not animation.title:
                errors.append(
                    f"Line {animation.line}: animation {animation.name!r} needs a title"
                )
            if self.version >= 2 and not animation.goal:
                errors.append(
                    f"Line {animation.line}: animation {animation.name!r} needs a goal"
                )
            if not animation.components:
                errors.append(
                    f"Line {animation.line}: animation {animation.name!r} has no components"
                )

        for beat in self.beats:
            if not beat.actions:
                errors.append(f"Line {beat.line}: cue {beat.cue!r} has no action")
            for action in _walk_actions(beat.actions):
                if action.verb not in ACTION_VERBS:
                    errors.append(
                        f"Line {action.line}: unknown action {action.verb!r}"
                    )
                role = action.option_map.get("role")
                if role and role not in SEMANTIC_ROLES:
                    errors.append(
                        f"Line {action.line}: unknown semantic role {role!r}"
                    )
                style = action.option_map.get("style")
                if action.verb == "focus" and style and style not in ATTENTION_STYLES:
                    errors.append(
                        f"Line {action.line}: unknown focus style {style!r}"
                    )
                if action.verb == "show" and style and style not in ENTRY_STYLES:
                    errors.append(
                        f"Line {action.line}: unknown entry style {style!r}"
                    )
                if action.verb == "hide" and style and style not in EXIT_STYLES:
                    errors.append(
                        f"Line {action.line}: unknown exit style {style!r}"
                    )

        if cue_path is not None:
            cue_path = Path(cue_path)
            cue_data = json.loads(cue_path.read_text(encoding="utf-8"))
            cue_times = {cue["name"]: float(cue["time"])
                         for cue in cue_data.get("cues", ())}
            previous_time = float("-inf")
            seen = set()
            for beat in self.beats:
                if beat.cue not in cue_times:
                    errors.append(
                        f"Line {beat.line}: cue {beat.cue!r} is absent from "
                        f"{cue_path.name}"
                    )
                    continue
                current_time = cue_times[beat.cue] + beat.offset
                if current_time < previous_time:
                    errors.append(
                        f"Line {beat.line}: cue {beat.cue!r} is out of time order"
                    )
                previous_time = current_time
                seen.add(beat.cue)
            if require_all_cues:
                missing = [name for name in cue_times if name not in seen]
                if missing:
                    errors.append("Missing cue beats: " + ", ".join(missing))

        if errors:
            raise StoryboardSyntaxError("\n".join(errors))
        return self

    def to_source(self):
        lines = [
            f"storyboard {self.version}",
            f"section {self.section} {json.dumps(self.title)}",
        ]
        if self.audio:
            lines.append(f"audio {json.dumps(self.audio)}")
        if self.objects:
            lines.append("")
            lines.extend(obj.to_source() for obj in self.objects.values())
        lines.append("")
        lines.extend(animation.to_source() + "\n" for animation in self.animations)
        return "\n".join(lines).rstrip() + "\n"

    def to_markdown(self):
        lines = [f"# {self.title}", "", f"Section: `{self.section}`", ""]
        for animation in self.animations:
            lines.extend([
                f"## {animation.title}", "", animation.goal, "",
            ])
            for beat in animation.components:
                spoken = f' — “{beat.phrase}”' if beat.phrase else ""
                lines.append(f"### `{beat.cue}`{spoken}")
                lines.append("")
                for action in beat.actions:
                    rendered = action.to_source(indent=0).replace("\n", " / ")
                    lines.append(f"- `{rendered}`")
                lines.append("")
        return "\n".join(lines)

    def density_warnings(self, cue_path=None, *, max_changes_per_phrase=4,
                         rapid_window=0.45):
        """Return review warnings for visually crowded or unmotivated beats."""
        warnings = []
        cue_times = {}
        if cue_path is not None:
            cue_data = json.loads(Path(cue_path).read_text(encoding="utf-8"))
            cue_times = {
                cue["name"]: float(cue["time"])
                for cue in cue_data.get("cues", ())
            }

        previous = None
        for animation in self.animations:
            for beat in animation.components:
                changes = _visual_action_count(beat.actions)
                if changes and not beat.phrase:
                    warnings.append(
                        f"{animation.name}/{beat.cue}: visual change has no spoken phrase"
                    )
                if changes > max_changes_per_phrase:
                    warnings.append(
                        f"{animation.name}/{beat.cue}: {changes} visual changes for one phrase"
                    )
                if beat.cue in cue_times:
                    instant = cue_times[beat.cue] + beat.offset
                    if previous is not None:
                        previous_instant, previous_changes, previous_label = previous
                        if (changes and previous_changes
                                and instant - previous_instant < rapid_window):
                            warnings.append(
                                f"{previous_label} -> {animation.name}/{beat.cue}: "
                                f"active beats are only {instant - previous_instant:.2f}s apart"
                            )
                    previous = (
                        instant, changes, f"{animation.name}/{beat.cue}",
                    )
        return warnings


def _walk_actions(actions):
    for action in actions:
        yield action
        yield from _walk_actions(action.children)


def _visual_action_count(actions):
    # A coordinated build is one beat, not a new idea per glyph/mobject. Cleanup
    # adds no competing content; rendered continuity checks audit large clears.
    quiet = {"hold", "note", "hide"}
    return sum((bool(_visual_action_count(action.children)) if action.verb == "together"
                else action.verb not in quiet) for action in actions)


def _parse_action(text, line_number):
    tokens = shlex.split(text, posix=True)
    if not tokens:
        raise StoryboardSyntaxError(f"Line {line_number}: empty action")
    verb = tokens[0]
    args = []
    options = []
    for token in tokens[1:]:
        if "=" in token and token not in {"=", "->"}:
            key, value = token.split("=", 1)
            options.append((key, value))
        else:
            args.append(token)
    return StoryAction(
        verb=verb, args=tuple(args), options=tuple(options), line=line_number,
    )


def parse_storyboard(text):
    version = None
    section = ""
    title = ""
    audio = ""
    objects = {}
    animations = []
    current_animation = None
    current_beat = None
    current_actions = []
    current_action_indent = 2
    together_stack = []

    def append_action(action):
        if together_stack:
            together_stack[-1][2].append(action)
        else:
            current_actions.append(action)

    def finish_together(min_indent=0):
        while together_stack and together_stack[-1][0] >= min_indent:
            _indent, line_number, children = together_stack.pop()
            action = StoryAction(
                "together", children=tuple(children), line=line_number,
            )
            append_action(action)

    def finish_beat():
        nonlocal current_beat, current_actions, current_animation
        if current_beat is None:
            return
        finish_together(0)
        cue, offset, phrase, line_number = current_beat
        if current_animation is None:
            current_animation = StoryAnimation(
                "timeline", title or "Timeline",
                "Phrase-triggered visual timeline.", line=line_number,
            )
        current_animation.components.append(StoryBeat(
            cue=cue, offset=offset, phrase=phrase,
            actions=tuple(current_actions), line=line_number,
        ))
        current_beat = None
        current_actions = []

    def finish_animation():
        nonlocal current_animation
        finish_beat()
        if current_animation is not None:
            animations.append(current_animation)
            current_animation = None

    def begin_beat(tokens, line_number, action_indent):
        nonlocal current_beat, current_action_indent
        cue = tokens[1]
        offset = 0.0
        phrase = ""
        cursor = 2
        if cursor < len(tokens) and tokens[cursor].startswith(("+", "-")):
            offset = float(tokens[cursor])
            cursor += 1
        if cursor < len(tokens):
            if tokens[cursor] != "say" or cursor + 1 >= len(tokens):
                raise StoryboardSyntaxError(
                    f"Line {line_number}: expected 'say \"phrase\"'"
                )
            phrase = tokens[cursor + 1]
        current_beat = (cue, offset, phrase, line_number)
        current_action_indent = action_indent

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if indent == 0:
            finish_beat()
            tokens = shlex.split(line[:-1] if line.endswith(":") else line,
                                 posix=True)
            if not tokens:
                continue
            if tokens[0] == "storyboard":
                version = int(tokens[1])
            elif tokens[0] == "section":
                section = tokens[1]
                title = tokens[2]
            elif tokens[0] == "audio":
                audio = tokens[1]
            elif tokens[0] == "object":
                if len(tokens) < 4:
                    raise StoryboardSyntaxError(
                        f"Line {line_number}: object needs name, kind, description"
                    )
                objects[tokens[1]] = StoryObject(
                    tokens[1], tokens[2], tokens[3], line_number,
                )
            elif tokens[0] == "animation":
                finish_animation()
                if len(tokens) < 3:
                    raise StoryboardSyntaxError(
                        f"Line {line_number}: animation needs an id and title"
                    )
                current_animation = StoryAnimation(
                    tokens[1], tokens[2], line=line_number,
                )
            elif tokens[0] == "at":
                begin_beat(tokens, line_number, 2)
            else:
                raise StoryboardSyntaxError(
                    f"Line {line_number}: unknown directive {tokens[0]!r}"
                )
            continue

        if indent == 2 and current_animation is not None:
            tokens = shlex.split(line[:-1] if line.endswith(":") else line,
                                 posix=True)
            if tokens and tokens[0] == "goal":
                if len(tokens) < 2:
                    raise StoryboardSyntaxError(
                        f"Line {line_number}: goal needs a description"
                    )
                current_animation.goal = tokens[1]
                continue
            if tokens and tokens[0] == "component":
                finish_beat()
                begin_beat(tokens, line_number, 4)
                continue

        if current_beat is None:
            raise StoryboardSyntaxError(
                f"Line {line_number}: actions must belong to a component"
            )
        if indent < current_action_indent or indent % 2:
            raise StoryboardSyntaxError(
                f"Line {line_number}: action indentation must be a multiple of two"
            )
        finish_together(indent)
        expected_indent = (
            current_action_indent
            if not together_stack else together_stack[-1][0] + 2
        )
        if indent != expected_indent:
            raise StoryboardSyntaxError(
                f"Line {line_number}: expected {expected_indent} spaces, got {indent}"
            )
        if line == "together:":
            together_stack.append([indent, line_number, []])
        else:
            append_action(_parse_action(line, line_number))

    finish_animation()
    if version is None:
        raise StoryboardSyntaxError("Missing 'storyboard 1' header")
    return Storyboard(
        section=section, title=title, audio=audio, version=version,
        objects=objects, animations=animations,
    )
