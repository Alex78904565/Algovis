"""Named mathematical terms laid out together by TeX, including substitutions."""
from __future__ import annotations
import numpy as np
from manim import FadeIn, FadeOut, MathTex, Transform, VectorizedPoint
from manim.mobject.text.tex_mobject import SCALE_FACTOR_PER_FONT_POINT


class MathRow(MathTex):
    """One native TeX baseline, with stable names for editable terms.

    Plan the complete next row, animate its affected terms, then ``commit``.
    Do not center a new digit on an old letter: their glyph boxes do not have
    the same relationship to the mathematical baseline.
    """
    _algovis_preserve_structure = True

    def __init__(self, parts, *, font_size=33.6, **kwargs):
        self.slot_tex = dict(parts)
        super().__init__(*self.slot_tex.values(), 'H', arg_separator='', font_size=font_size, **kwargs)
        marker = self.submobjects[-1]
        origin = np.array([self.get_left()[0], marker.get_bottom()[1], 0.])
        self.remove(marker)
        self.parts = dict(zip(self.slot_tex, self.submobjects))
        # TeX part containers may report white while their glyphs are blue.
        # Normalize uniform paint onto the named term so later substitutions
        # retain its semantic color instead of silently turning it white.
        for part in self.parts.values():
            colors={p.get_fill_color().to_hex() for p in part.family_members_with_points()
                    if float(np.max(p.get_fill_opacity()))>.01}
            if len(colors)==1:part.set_color(next(iter(colors)))
        self._axis_origin = VectorizedPoint(origin)
        self._axis_unit = VectorizedPoint(origin + [.01, 0, 0])
        self.add(self._axis_origin, self._axis_unit)
        self._native_size = float(font_size)
        self.tex_string = ''.join(self.slot_tex.values())
        self._remember_layout()

    @property
    def font_size(self):
        if '_axis_unit' in self.__dict__:
            return self._native_size*self._scale()
        return super().font_size

    @font_size.setter
    def font_size(self, value):
        MathTex.font_size.fset(self, value)

    @property
    def baseline(self):
        return float(self._axis_origin.get_center()[1])

    def part(self, name):
        return self.parts[name]

    def _scale(self):
        return float(np.linalg.norm(self._axis_unit.get_center()-self._axis_origin.get_center())/.01)

    def _remember_layout(self):
        origin = self._axis_origin.get_center(); scale = self._scale()
        self._native_geometry = {name: ((part.get_center()-origin)/scale,
                                       float(part.width)/scale, float(part.height)/scale)
                                 for name,part in self.parts.items()}

    def aligned_to(self, other):
        self.shift([other.get_left()[0]-self.get_left()[0], other.baseline-self.baseline, 0])
        return self

    def next_layout(self, parts=None, **changes):
        values = dict(parts) if parts is not None else {**self.slot_tex, **changes}
        target = MathRow(values, font_size=self._native_size*self._scale(), color=self.get_color())
        for name,part in target.parts.items():
            if name in self.parts:
                part.set_color(self.parts[name].get_color())
        if hasattr(self, '_sum_contract'): target._sum_contract = self._sum_contract
        return target.aligned_to(self)

    def require_sum(self, immediate='immediate', future='future', total='total'):
        """Check explicitly additive numerical worked examples when completed."""
        self._sum_contract = (immediate,future,total)
        return self

    def motions_to(self, target, *, skip=()):
        skip = set(skip); animations = []
        for name,part in self.parts.items():
            if name in skip: continue
            animations.append(Transform(part,target.part(name)) if name in target.parts else FadeOut(part))
        animations.extend(FadeIn(part) for name,part in target.parts.items()
                          if name not in self.parts and name not in skip)
        return animations

    def commit(self, target, scene):
        """Adopt the exact native layout, preserving unchanged term owners."""
        old = self.parts.copy(); old_family = list(self.get_family())
        scene.remove(*old_family, *target.get_family())
        adopted = {}
        for name,new in target.parts.items():
            part = old.get(name, new)
            if part is not new:
                part.become(new)
                part.submobjects = [child.copy() for child in new.submobjects]
            part._algovis_label = target.slot_tex[name]
            if part.height>0:
                part.initial_height = part.height/(target.font_size*SCALE_FACTOR_PER_FONT_POINT)
            adopted[name] = part
        self.parts = adopted; self.slot_tex = target.slot_tex.copy()
        self._axis_origin = target._axis_origin.copy(); self._axis_unit = target._axis_unit.copy()
        self.submobjects = [*adopted.values(),self._axis_origin,self._axis_unit]
        self._native_size = target._native_size*target._scale()
        self._remember_layout()
        self._algovis_label = ''.join(self.slot_tex.values())
        self.tex_string = self._algovis_label
        if hasattr(target, '_sum_contract'): self._sum_contract = target._sum_contract
        scene.add(self)
        if getattr(self, '_algovis_typography_group', None):
            from ..layout import LessonStyle
            LessonStyle._watch_type(self,self._algovis_typography_group,'equation')
        if hasattr(scene,'_capture_review_snapshot'): scene._capture_review_snapshot()

    def native_layout_findings(self, tolerance=.003):
        origin = self._axis_origin.get_center(); scale = self._scale(); findings = []
        for name,part in self.parts.items():
            center,width,height = self._native_geometry[name]
            drift = float(np.linalg.norm(part.get_center()-(origin+center*scale)))
            size_error = max(abs(part.width-width*scale),abs(part.height-height*scale))
            if max(drift,size_error)>tolerance:
                findings.append({'part':name,'positionError':drift,'sizeError':float(size_error)})
        if hasattr(self,'_sum_contract'):
            try:
                immediate,future,total = (int(self.slot_tex[name]) for name in self._sum_contract)
            except (KeyError,ValueError):
                pass  # The symbolic or not-yet-completed stage has no sum yet.
            else:
                if immediate+future != total:
                    findings.append({'arithmetic':'incorrect additive result','expected':immediate+future,'actual':total})
        return findings
