"""Object meaning, resolved by the theme rather than by last-applied paint."""
from dataclasses import asdict, dataclass, replace

from manim import Transform

from .theme import DEFAULT_THEME


@dataclass(frozen=True)
class SemanticProperties:
    """Independent facts about an object; evaluation has highest precedence."""

    role: str = 'neutral'
    status: str | None = None
    evaluation: str | None = None

    def __post_init__(self):
        if self.evaluation not in (None, 'good', 'bad'):
            raise ValueError('Evaluation must be good, bad, or unspecified')
        if self.status not in (None, 'unseen', 'active', 'known', 'computed',
                               'stored', 'selected', 'valid', 'complete',
                               'invalid', 'rejected', 'repeated'):
            raise ValueError(f'Unknown semantic status: {self.status!r}')

    def roles(self):
        roles = [self.role]
        if self.status in ('known', 'computed', 'stored', 'selected', 'valid', 'complete'):
            roles.append('retained')
        elif self.status == 'active':
            roles.append('operation')
        elif self.status in ('invalid', 'rejected', 'repeated'):
            roles.append('bad')
        if self.evaluation:
            roles.append(self.evaluation)
        return tuple(roles)

    def color(self, theme=DEFAULT_THEME):
        return theme.role_color(*self.roles())


def set_semantics(mobject, properties=None, *, theme=None, part=None, channel=None, **changes):
    """Store properties on any Manim object and derive its paint together.

    ``part='box', channel='stroke'`` styles a cell's frame while keeping its
    value neutral. Copies preserve this binding. Use SemanticChange on a
    spoken cue when changing the meaning of an already visible object.
    """
    current = properties or getattr(mobject, 'semantics', SemanticProperties())
    properties = replace(current, **changes) if changes else current
    theme = theme or getattr(mobject, '_semantic_theme', DEFAULT_THEME)
    part = part if part is not None else getattr(mobject, '_semantic_part', None)
    channel = channel or getattr(mobject, '_semantic_channel', 'color')
    if channel not in ('color', 'stroke'):
        raise ValueError('Semantic paint channel must be color or stroke')
    color = properties.color(theme)  # Validate before mutating the object.
    target = getattr(mobject, part) if part else mobject
    if channel == 'stroke':
        target.set_stroke(color=color)
    else:
        target.set_color(color)
    mobject.semantics = properties
    mobject._semantic_theme = theme
    mobject._semantic_part = part
    mobject._semantic_channel = channel
    mobject._algovis_semantics = asdict(properties)
    mobject._algovis_semantic_role = properties.role
    paint=getattr(type(mobject),'apply_semantic_paint',None)
    if paint is not None:
        paint(mobject,properties,theme,part=part,channel=channel)
    return mobject


def copy_semantics(source, target):
    """Carry declared meaning through a native mathematical substitution."""
    if hasattr(source, 'semantics'):
        target.semantics = source.semantics
        for name in ('_semantic_theme', '_semantic_part', '_semantic_channel',
                     '_algovis_semantic_role', '_algovis_semantics'):
            if hasattr(source, name):
                setattr(target, name, getattr(source, name))
    return target


class SemanticChange(Transform):
    """Animate a property change without recoloring live objects during a wait."""

    def __init__(self, mobject, properties=None, *, theme=None, **changes):
        target = set_semantics(mobject.copy(), properties, theme=theme, **changes)
        self.properties = target.semantics
        self.semantic_theme = target._semantic_theme
        self.semantic_part = target._semantic_part
        self.semantic_channel = target._semantic_channel
        super().__init__(mobject, target)

    def finish(self):
        super().finish()
        set_semantics(self.mobject, self.properties, theme=self.semantic_theme,
                      part=self.semantic_part, channel=self.semantic_channel)
