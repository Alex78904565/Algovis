"""Select immutable, completed render revisions for downstream video assembly."""
from pathlib import Path


def completed_render(workspace: Path, scene: str, section: str, *, video_dir: Path) -> Path:
    """Prefer the published revision; fall back to the ordinary Manim output.

    Manim may rewrite its scene output while rendering, so assembly should
    snapshot these completed paths before starting. An in-progress publisher
    file must never be mistaken for a completed revision.
    """
    revisions = [
        path for path in (workspace / ".review" / "renders" / section).glob("*.mp4")
        if not path.name.endswith(".tmp.mp4")
    ]
    if revisions:
        return max(revisions, key=lambda path: path.stat().st_mtime_ns)
    return video_dir / f"{scene}.mp4"
