from dataclasses import dataclass, replace
from manim import BLUE_B, BLUE_C, GREEN_B, GREY_B, RED_B, WHITE, YELLOW


@dataclass(frozen=True)
class AlgovisSpacing:
    """One spacing scale for slide layouts and reusable components."""

    micro: float = 0.08
    tight: float = 0.16
    normal: float = 0.28
    relaxed: float = 0.42
    section: float = 0.62


DEFAULT_SPACING = AlgovisSpacing()


@dataclass(frozen=True)
class AlgovisTheme:
    """Semantic colors shared by an Algovis video.

    ``primary`` is structural, ``accent`` marks the current focus,
    ``success`` means known/computed/correct, ``danger`` marks wasted work or
    warnings, ``foreground`` is neutral mathematics, and ``muted`` is context.
    Components should use these roles instead of importing arbitrary colors.
    """

    background: object = "#0B1020"
    surface: object = "#111A30"
    foreground: object = WHITE
    primary: object = BLUE_B
    node: object = BLUE_C
    accent: object = YELLOW
    success: object = GREEN_B
    danger: object = RED_B
    muted: object = GREY_B

    def with_colors(self, **changes):
        """Return a copy with selected semantic colors replaced."""
        return replace(self, **changes)

    def apply(self, scene):
        scene.camera.background_color = self.background
        return scene


DEFAULT_THEME = AlgovisTheme()
LIGHT_THEME = AlgovisTheme(
    background="#F7F4EC", surface="#FFFFFF", foreground="#172033",
    primary="#176B87", node="#2389A8", accent="#D99000",
    success="#2E7D32", danger="#B3261E", muted="#59636E",
)
WARM_THEME = AlgovisTheme(
    background="#17120F", surface="#2A201A", foreground="#FFF7EA",
    primary="#F2A65A", node="#D9824B", accent="#FFD166",
    success="#7BC67B", danger="#EF6F6C", muted="#B9AAA0",
)
NIGHTCLUB_THEME = AlgovisTheme(
    background="#08040F",
    surface="#180B2D",
    foreground="#FAF2FF",
    primary="#B66CFF",
    node="#8B5CF6",
    accent="#FF4FD8",
    success="#43E8FF",
    danger="#FF3B81",
    muted="#A995BD",
)
