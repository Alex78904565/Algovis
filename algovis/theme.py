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

    ``primary`` is structural and supplies neutral spoken attention,
    ``accent`` marks an active operation, choice, or optimizer,
    Explicit good/bad evaluation takes precedence over every other role:
    ``success`` is favorable and ``danger`` is unfavorable for the stated goal.
    Otherwise known/computed/correct uses ``success``, followed by operation,
    structure and neutral/context roles. ``role_color`` resolves competing roles.
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
    text_font: str | None = None

    def with_colors(self, **changes):
        """Return a copy with selected semantic colors replaced."""
        return replace(self, **changes)

    def with_typography(self, *, text_font=None):
        """Return a copy with a default font for ordinary ``Text`` objects."""
        return replace(self, text_font=text_font)

    def role_color(self, role, *other_roles):
        """Resolve roles by meaning, independently of their argument order.

        Evaluation > completed/known status > operation > structure > context.
        For example, ``role_color('retained', 'bad')`` is danger-colored even
        though the poor result is correctly derived. Contradictory explicit
        evaluations must be resolved by the author, rather than by call order.
        """
        colors = {
            "neutral": self.foreground,
            "current": self.primary,
            "operation": self.accent,
            "retained": self.success,
            "repeated": self.danger,
            # Friendly aliases used by lower-level components.
            "structure": self.primary,
            "node": self.node,
            "success": self.success,
            "danger": self.danger,
            "muted": self.muted,
            "good": self.success,
            "bad": self.danger,
        }
        roles = (role, *other_roles)
        for candidate in roles:
            if candidate not in colors:
                raise ValueError(f"Unknown semantic color role: {candidate!r}")
        negative = {'bad', 'danger', 'repeated'}
        if 'good' in roles and negative.intersection(roles):
            raise ValueError('Conflicting good/bad evaluations need an explicit context')
        priority = {
            'good': 5, 'bad': 5, 'danger': 5, 'repeated': 5,
            'retained': 4, 'success': 4,
            'operation': 3,
            'current': 2, 'structure': 2, 'node': 2,
            'muted': 1, 'neutral': 0,
        }
        return colors[max(roles, key=priority.__getitem__)]

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
