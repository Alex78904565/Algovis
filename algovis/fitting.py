"""Readable, uniform fitting for detached layout plans."""
from dataclasses import dataclass
import math

from .layout import LessonStyle, measured_font_size


@dataclass(frozen=True)
class FitPolicy:
    enabled: bool = True
    min_scale: float = .72
    min_font_size: float = 16
    wrap_text: bool = True

    def __post_init__(self):
        if not math.isfinite(self.min_scale) or not 0 < self.min_scale <= 1:
            raise ValueError('Minimum fit scale must lie between zero and one')
        if not math.isfinite(self.min_font_size) or self.min_font_size <= 0:
            raise ValueError('Minimum fitted font size must be positive')

    def check(self, items, scale):
        if scale < self.min_scale-1e-7:
            raise ValueError('Content exceeds the readable layout capacity; split the content or choose another layout')
        for item in items:
            if any(size*scale < self.min_font_size-1e-7 for size in font_sizes(item.target)):
                raise ValueError('Content exceeds the readable layout capacity: fitting would make text too small')


@dataclass
class FitArea:
    """Areas with the same group name share one fitting scale."""
    group: str
    items: list
    width: float
    height: float
    stacked: bool = False
    gap: float = 0

    def scale(self, heights):
        if not self.items:
            return 1.
        width = max(item.target.width for item in self.items)
        sizes = [heights(item) for item in self.items]
        height = sum(sizes) if self.stacked else max(sizes)
        available = self.height-self.gap*max(0,len(self.items)-1) if self.stacked else self.height
        return min(1., self.width/max(width,1e-9), available/max(height,1e-9))


def font_sizes(mobject):
    size=measured_font_size(mobject)
    if size is not None and size>0:
        return [float(size)]
    return [size for child in mobject.submobjects for size in font_sizes(child)]


def font_only(mobject):
    if measured_font_size(mobject):return True
    if mobject.has_points():return False
    children=[child for child in mobject.submobjects if child.has_points() or child.submobjects]
    return bool(children) and all(font_only(child) for child in children)


def relative_font_scale(mobject, factor):
    if not math.isfinite(factor) or factor<=0:
        raise ValueError('Relative font scale must be positive and finite')
    if factor!=1 and not font_only(mobject):
        raise TypeError('font_scale needs text or an equation; style diagram labels through their component')
    for part in mobject.get_family():
        part._algovis_relative_font_scale=float(factor)


def plain_text(text, width, *, theme, wrap=True, typography=None, type_role='body'):
    """Wrap ordinary prose before shrinking; equations retain their syntax."""
    style = LessonStyle(theme=theme, **({'typography': typography} if typography else {}))
    make = lambda value: style.text(value, type_role=type_role)
    if not wrap:
        return make(text)
    lines = []
    for paragraph in str(text).split('\n'):
        line = ''
        for word in paragraph.split():
            candidate = (line+' '+word).strip()
            if line and make(candidate).width > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    result = make('\n'.join(lines))
    result._algovis_source_text = str(text)
    result._algovis_label = str(text)
    return result
