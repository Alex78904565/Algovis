"""Static preflight checks for cue-driven Algovis lessons.

The checks are deliberately conservative.  They identify sections that need a
human look; they do not pretend that source inspection can certify a render.
"""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re

from .storyboard import Storyboard, StoryboardSyntaxError
from .review.audit import tokens as _spoken_tokens, timed_words as _spoken_words


@dataclass(frozen=True)
class AuditIssue:
    severity: str
    category: str
    message: str
    location: str = ""
    cue: str | None = None
    time: float | None = None


@dataclass
class SectionAudit:
    id: str
    title: str
    issues: list[AuditIssue] = field(default_factory=list)
    annotation_counts: dict[str, int] = field(default_factory=dict)

    @property
    def status(self) -> str:
        if any(issue.severity == "error" for issue in self.issues):
            return "blocked"
        if self.annotation_counts.get("pending", 0) or self.annotation_counts.get("draft", 0):
            return "blocked"
        if self.annotation_counts.get("pending_review", 0):
            return "needs_review"
        if any(issue.severity == "warning" for issue in self.issues):
            return "needs_review"
        return "ready"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "annotationCounts": self.annotation_counts,
            "issues": [asdict(issue) for issue in self.issues],
        }


def _tokens(value: str) -> list[str]:
    return _spoken_tokens(value)


def _transcript_tokens(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    tokens = []
    for word in _spoken_words(data):
        tokens.extend(_tokens(str(word.get("word", ""))))
    if not tokens:
        tokens = _tokens(str(data.get("text", "")))
    return tokens


def _contains_phrase(words: list[str], phrase: str) -> bool:
    wanted = _tokens(phrase)
    if not wanted:
        return False
    size = len(wanted)
    return any(words[index:index + size] == wanted
               for index in range(max(0, len(words) - size + 1)))


def timed_transcript_tokens(path: Path) -> list[tuple[str, float]]:
    """Chronological words, without repeated ASR context at segment joins."""
    data = json.loads(path.read_text(encoding="utf-8"))
    words = _spoken_words(data)
    seen, result = set(), []
    for word in words:
        key = (word["start"], word["end"], word["word"])
        if key in seen:
            continue
        seen.add(key)
        result.extend((token, float(word["start"])) for token in _tokens(word["word"]))
    return result


def phrase_anchor_offset(words: list[tuple[str, float]], phrase: str, time: float) -> float | None:
    """Return how far the nearest actual phrase is from the proposed trigger."""
    wanted = _tokens(phrase)
    if not wanted:
        return None
    tokens = [word[0] for word in words]
    matches = [words[index][1] for index in range(len(words) - len(wanted) + 1)
               if tokens[index:index + len(wanted)] == wanted]
    if not matches:
        return None
    return min(matches, key=lambda match: abs(match-time)) - time


def _method(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    return next(
        (node for node in ast.walk(tree)
         if isinstance(node, ast.FunctionDef) and node.name == name),
        None,
    )


def _call_name(node: ast.Call) -> str:
    target = node.func
    if isinstance(target, ast.Attribute):
        return target.attr
    if isinstance(target, ast.Name):
        return target.id
    return ""


def _literal(node, default=None):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return default


def audit_source_method(
    source_tree: ast.AST,
    method_name: str,
    cue_names: set[str],
    source_name: str,
    cue_times: dict[str, float] | None = None,
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    method = _method(source_tree, method_name)
    if method is None:
        return [AuditIssue(
            "error", "source", f"Scene method {method_name!r} was not found.",
            source_name,
        )]

    # Ignore legacy source deliberately parked after a top-level ``return``.
    # It is useful reference material, but it cannot affect the rendered clip.
    reachable_body = []
    for statement in method.body:
        if isinstance(statement, ast.Return):
            break
        reachable_body.append(statement)
    reachable = ast.Module(body=reachable_body, type_ignores=[])

    cue_times = cue_times or {}
    anchors = []
    for statement in reachable_body:
        # Helper function bodies run later; their source position is not a
        # reliable place on the narration timeline.
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for call in ast.walk(statement):
            if not isinstance(call, ast.Call) or _call_name(call) != "wait_for_cue":
                continue
            cue = _literal(call.args[0]) if call.args else None
            if not isinstance(cue, str):
                continue
            offset = next((
                _literal(keyword.value, 0.0)
                for keyword in call.keywords if keyword.arg == "offset"
            ), 0.0)
            anchors.append((call.lineno, cue, float(offset or 0.0)))
    anchors.sort()

    def moment(line):
        prior = [anchor for anchor in anchors if anchor[0] <= line]
        if not prior:
            return None, None
        _line, cue, offset = prior[-1]
        time = cue_times.get(cue)
        return cue, max(0.0, time + offset) if time is not None else None

    hard_wait_lines = []
    large_offsets = []
    semantic_indicates = []
    used_cues = set()
    indicate_count = 0
    play_count = 0
    for node in ast.walk(reachable):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in {"play", "transition"}:
            play_count += 1
        elif name == "wait":
            hard_wait_lines.append(node.lineno)
        elif name == "wait_for_cue":
            cue = _literal(node.args[0]) if node.args else None
            if isinstance(cue, str):
                used_cues.add(cue)
                if cue not in cue_names:
                    issues.append(AuditIssue(
                        "error", "timing",
                        f"Source references unknown cue {cue!r}.",
                        f"{source_name}:{node.lineno}",
                    ))
            for keyword in node.keywords:
                if keyword.arg == "offset":
                    offset = _literal(keyword.value)
                    if isinstance(offset, (int, float)) and abs(offset) > 0.75:
                        large_offsets.append((node.lineno, float(offset)))
        elif name in {"Indicate", "Pulse"}:
            indicate_count += 1
            for keyword in node.keywords:
                if keyword.arg == "color":
                    color = ast.unparse(keyword.value)
                    if any(term in color for term in (
                        "success", "danger", "GREEN", "RED",
                    )):
                        semantic_indicates.append((node.lineno, color))

    for line in hard_wait_lines:
        next_control = next((call for call in sorted(
            (call for call in ast.walk(reachable) if isinstance(call, ast.Call)
             and call.lineno > line and _call_name(call) in {
                 "wait_for_cue", "play_to_cue", "play", "transition", "finish_narration",
             }), key=lambda call: call.lineno)), None)
        if next_control is None or _call_name(next_control) in {
            "wait_for_cue", "play_to_cue", "finish_narration",
        }:
            # A still hold before another named cue does not move that cue.
            # The rendered late-arrival check detects an actual overrun.
            continue
        cue, time = moment(line)
        issues.append(AuditIssue(
            "warning", "timing",
            "Hard-coded wait bypasses the narration timeline; check its timing.",
            f"{source_name}:{line}", cue, time,
        ))
    for line, offset in large_offsets:
        cue, time = moment(line)
        issues.append(AuditIssue(
            "warning", "timing",
            f"Cue offset {offset:+.2f}s is large; prefer a word-level cue.",
            f"{source_name}:{line}", cue, time,
        ))
    for line, color in semantic_indicates:
        cue, time = moment(line)
        issues.append(AuditIssue(
            "info", "color",
            f"Indicate uses semantic color {color}; confirm the object's meaning changes, otherwise use blue/outline attention.",
            f"{source_name}:{line}", cue, time,
        ))
    if indicate_count > max(8, len(cue_names) // 2):
        issues.append(AuditIssue(
            "warning", "density",
            f"{indicate_count} Indicate animations may create gratuitous flashing.",
            method_name,
        ))
    if used_cues and play_count / len(used_cues) > 3.0:
        issues.append(AuditIssue(
            "warning", "density",
            f"{play_count} play calls across {len(used_cues)} timed cues; audit for rapid slide-like changes.",
            method_name,
        ))
    return issues


def audit_project(
    workspace: Path,
    config_path: Path,
    *,
    storyboard_by_section: dict[str, Path],
    method_by_section: dict[str, str],
    source_path: Path,
) -> dict:
    workspace = workspace.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_tree = ast.parse(source_path.read_text(encoding="utf-8"))
    reports = []

    for section in config.get("sections", []):
        section_id = section["id"]
        report = SectionAudit(section_id, section.get("title", section_id))
        required = ("video", "cues", "transcriptWords", "audio")
        for key in required:
            value = section.get(key)
            if not value or not (workspace / value).exists():
                report.issues.append(AuditIssue(
                    "error", "assets", f"Missing {key} asset: {value or '(not configured)'}",
                ))
        music = section.get("music")
        if not music or not (workspace / music).exists():
            report.issues.append(AuditIssue(
                "warning", "audio", "No review music file is available for this section.",
            ))

        cue_path = workspace / section["cues"]
        cue_names: set[str] = set()
        cue_times: dict[str, float] = {}
        if cue_path.exists():
            cue_data = json.loads(cue_path.read_text(encoding="utf-8"))
            cues = list(cue_data.get("cues", []))
            names = [str(cue.get("name", "")) for cue in cues]
            cue_names = set(names)
            cue_times = {str(cue["name"]): float(cue.get("time", 0.0)) for cue in cues}
            duplicates = [name for name, count in Counter(names).items() if name and count > 1]
            if duplicates:
                report.issues.append(AuditIssue(
                    "error", "timing", "Duplicate cue names: " + ", ".join(duplicates),
                    section["cues"],
                ))
            times = [float(cue.get("time", 0.0)) for cue in cues]
            if times != sorted(times):
                report.issues.append(AuditIssue(
                    "error", "timing", "Cue times are not monotonic.", section["cues"],
                ))
            duration = float(cue_data.get("duration", 0.0))
            # Cue files are rounded to milliseconds while media duration often
            # retains sub-millisecond precision.
            if times and duration and max(times) > duration + 0.05:
                report.issues.append(AuditIssue(
                    "error", "timing", "A cue occurs after the section duration.", section["cues"],
                ))

            transcript_path = workspace / section.get("transcriptWords", "")
            if transcript_path.exists():
                words = _transcript_tokens(transcript_path)
                timed_words = timed_transcript_tokens(transcript_path)
                for cue in cues:
                    if cue.get("name") in {"section_start", "section_end"}:
                        continue
                    offset = phrase_anchor_offset(timed_words, str(cue.get("phrase", "")), float(cue["time"]))
                    if offset is not None and abs(offset) > 1.0:
                        report.issues.append(AuditIssue(
                            "warning", "timing",
                            f"Cue phrase is spoken {abs(offset):.2f}s "
                            f"{'after' if offset > 0 else 'before'} its trigger; verify the word anchor.",
                            section.get("transcriptWords", ""), cue["name"], float(cue["time"]),
                        ))
                unmatched = [
                    cue.get("name", "") for cue in cues
                    if cue.get("phrase") and not _contains_phrase(words, str(cue["phrase"]))
                ]
                for cue_name in unmatched:
                    report.issues.append(AuditIssue(
                        "warning", "timing",
                        f"Cue phrase for {cue_name!r} is not an exact transcript match; verify its anchor.",
                        section.get("transcriptWords", ""),
                        cue_name, cue_times.get(cue_name),
                    ))

        board_path = storyboard_by_section.get(section_id)
        if board_path is None or not board_path.exists():
            report.issues.append(AuditIssue(
                "error", "storyboard", "No storyboard is mapped to this section.",
            ))
        else:
            try:
                board = Storyboard.load(board_path)
                board.validate(cue_path, require_all_cues=True)
                for warning in board.density_warnings(cue_path):
                    labels = re.findall(r"(?:^| -> )[^ /:]+/([^ :]+)", warning)
                    cue = labels[-1] if labels else None
                    beats = board.beats_for(cue) if cue else ()
                    offset = beats[0].offset if beats else 0.0
                    time = cue_times.get(cue)
                    report.issues.append(AuditIssue(
                        "warning", "storyboard", warning,
                        str(board_path.relative_to(workspace)),
                        cue, time + offset if time is not None else None,
                    ))
            except (StoryboardSyntaxError, ValueError, json.JSONDecodeError) as exc:
                report.issues.append(AuditIssue(
                    "error", "storyboard", str(exc),
                    str(board_path.relative_to(workspace)),
                ))

        method_name = method_by_section.get(section_id)
        if method_name:
            report.issues.extend(audit_source_method(
                source_tree, method_name, cue_names, source_path.name, cue_times,
            ))
        else:
            report.issues.append(AuditIssue(
                "error", "source", "No scene method is mapped to this section.",
            ))

        annotation_path = (
            workspace / ".review" / "annotations" / section_id / "annotations.json"
        )
        annotations = []
        if annotation_path.exists():
            try:
                annotations = json.loads(annotation_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                report.issues.append(AuditIssue(
                    "error", "review", "Annotation queue is not valid JSON.",
                    str(annotation_path.relative_to(workspace)),
                ))
        report.annotation_counts = dict(Counter(
            str(item.get("status", "draft")) for item in annotations
        ))
        reports.append(report)

    status_counts = Counter(report.status for report in reports)
    return {
        "schemaVersion": 1,
        "summary": dict(status_counts),
        "sections": {report.id: report.to_dict() for report in reports},
    }


def audit_markdown(data: dict) -> str:
    sections = list(data.get("sections", {}).values())
    lines = [
        "# Current animation audit", "",
        "Generated by `python tools/audit_animation_setup.py`. Static checks flag",
        "review risk; they do not replace watching the rendered section.", "",
        "## Summary", "",
        "| Status | Sections |", "|---|---:|",
    ]
    summary = data.get("summary", {})
    for status in ("ready", "needs_review", "blocked"):
        lines.append(f"| {status.replace('_', ' ').title()} | {summary.get(status, 0)} |")
    lines.extend(["", "## Section gates", "", "| Section | Gate | Open notes | Findings |", "|---|---|---:|---:|"])
    for section in sections:
        counts = section.get("annotationCounts", {})
        open_notes = sum(counts.get(key, 0) for key in ("draft", "pending", "pending_review"))
        lines.append(
            f"| {section['title']} | **{section['status'].replace('_', ' ')}** | "
            f"{open_notes} | {len(section.get('issues', []))} |"
        )
    for section in sections:
        lines.extend(["", f"## {section['title']}", "", f"Gate: **{section['status'].replace('_', ' ')}**", ""])
        issues = section.get("issues", [])
        if not issues:
            lines.append("- No static findings.")
        for issue in issues:
            location = f" (`{issue['location']}`)" if issue.get("location") else ""
            lines.append(
                f"- **{issue['severity'].upper()} · {issue['category']}**: "
                f"{issue['message']}{location}"
            )
        counts = section.get("annotationCounts", {})
        if counts:
            rendered = ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))
            lines.append(f"- **REVIEW**: {rendered}.")
    return "\n".join(lines) + "\n"
