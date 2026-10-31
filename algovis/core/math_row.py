"""Named mathematical terms laid out together by TeX, including substitutions."""
from __future__ import annotations
import numpy as np
import re
from manim import AnimationGroup, FadeIn, FadeOut, MathTex, Succession, Transform, VectorizedPoint, VGroup
from manim.mobject.text.tex_mobject import SCALE_FACTOR_PER_FONT_POINT


class MathRow(MathTex):
    """One native TeX baseline, with stable names for editable terms.

    Plan the complete next row, animate its affected terms, then ``commit``.
    Do not center a new digit on an old letter: their glyph boxes do not have
    the same relationship to the mathematical baseline.
    """
    _algovis_preserve_structure = True

    @classmethod
    def tokens(cls, *tex, **kwargs):
        """Adopt an existing tokenized equation without inventing term names.

        Numeric token indices remain usable. Prefer named parts for new code;
        use ``part(str(index))`` rather than negative indices (the final two
        children are invisible baseline anchors).
        """
        # This adapter replaces MathTex(...).scale(...), whose default is 48.
        # The named-row authoring API keeps its own 33.6-point default.
        kwargs.setdefault('font_size',48)
        return cls({str(i): value for i, value in enumerate(tex)}, **kwargs)

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
        if name.endswith('*'):
            matches=[part for key,part in self.parts.items() if key.startswith(name[:-1])]
            if not matches:raise KeyError(name)
            group=VGroup(*matches)
            group.tex_string=''.join(value for key,value in self.slot_tex.items() if key.startswith(name[:-1]))
            return group
        return self.parts[name]

    def get_part_by_tex(self, tex, **kwargs):
        if 'parts' not in self.__dict__:
            return super().get_part_by_tex(tex,**kwargs)
        return next((self.parts[name] for name,value in self.slot_tex.items() if value==tex),None)

    def set_color_by_tex(self, tex, color, **kwargs):
        if 'parts' not in self.__dict__:
            return super().set_color_by_tex(tex,color,**kwargs)
        for name,value in self.slot_tex.items():
            if value==tex:self.parts[name].set_color(color)
        return self

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
        from ..semantics import copy_semantics
        values = dict(parts) if parts is not None else {**self.slot_tex, **changes}
        meaning=getattr(self,'semantics',None)
        color=meaning.color(self._semantic_theme) if meaning is not None else self.get_color()
        target = MathRow(values, font_size=self._native_size*self._scale(), color=color)
        for name,part in target.parts.items():
            if name in self.parts:
                part.set_color(self.parts[name].get_color())
                copy_semantics(self.parts[name],part)
        copy_semantics(self,target)
        if hasattr(self, '_sum_contract'): target._sum_contract = self._sum_contract
        return target.aligned_to(self)

    def require_sum(self, immediate='immediate', future='future', total='total'):
        """Check explicitly additive numerical worked examples when completed."""
        self._sum_contract = (immediate,future,total)
        return self

    def with_state(self,*,parts=None,**changes):
        """Refine a named equation inside a layout container's state model."""
        return self.next_layout(parts,**changes)

    def annotation_parts(self,part,tex=None):
        """Plan a native underbrace without replacing its named operand.

        The annotation has neutral ink while the operand keeps its own meaning.
        Passing None removes that annotation, retaining the operand and peers.
        """
        if part not in self.parts:raise KeyError(part)
        before,after=f'annotation:{part}:open',f'annotation:{part}:close'
        result={}
        for name,value in self.slot_tex.items():
            if name in (before,after):continue
            if name==part and tex is not None:result[before]=r'\underbrace{'
            result[name]=value
            if name==part and tex is not None:result[after]='}_{'+str(tex)+'}'
        return result

    def prose_term(self, name):
        """Whether a named term begins with explanatory words, not a call."""
        return bool(re.match(
            r'^(?:\s|[({\[]|\\(?:quad|qquad|left|bigl|Bigl|biggl|Biggl|,|;|!| ))*\\text\{',
            self.slot_tex[name]))

    def motions_to(self, target, *, skip=(), introductions=None, retirements=None):
        from ..utils.effects import DeferredAnimation, ReplaceContent
        skip = set(skip); animations = []; retired = []; replacements=[]
        for name,part in self.parts.items():
            if name in skip: continue
            if name not in target.parts:
                retired.append(FadeOut(part))
            elif (re.findall(r'\\text\{([^{}]*)\}',self.slot_tex[name])
                  !=re.findall(r'\\text\{([^{}]*)\}',target.slot_tex[name])
                  and any(re.search(r'[A-Za-z]\([^)]*\)\s*\\text\{',tex)
                          for tex in (self.slot_tex[name],target.slot_tex[name]))):
                raise ValueError('Changing prose appended to a function call requires separate named math and prose terms: '+name)
            elif ((self.prose_term(name) or target.prose_term(name))
                  and re.findall(r'\\text\{([^{}]*)\}',self.slot_tex[name])
                  != re.findall(r'\\text\{([^{}]*)\}',target.slot_tex[name])):
                # Prose is a caption, not a glyph-wise algebraic substitution.
                # Keep the surrounding equation while changing its words locally.
                if retirements is None:animations.append(ReplaceContent(part,target.part(name)))
                else:
                    retired.append(FadeOut(part));replacements.append(target.part(name))
            else:
                animations.append(Transform(part,target.part(name)))
        introduced = replacements+[part for name,part in target.parts.items()
                                   if name not in self.parts and name not in skip]
        if retirements is not None:
            retirements.extend(retired)
            retired=[]
        if introductions is not None:
            # A containing equation owns one arrival phase for all its rows.
            introductions.extend(introduced)
            introduced=[]
        moving=any(np.linalg.norm(self.part(name).get_center()-target.part(name).get_center())>.1
                   for name in self.parts.keys() & target.parts.keys() if name not in skip)
        def arrival():
            if moving and introduced:
                return Succession(AnimationGroup(*animations,run_time=.8),
                    DeferredAnimation(lambda:AnimationGroup(*(FadeIn(part) for part in introduced)),run_time=.2))
            return AnimationGroup(*animations,*(FadeIn(part) for part in introduced))
        if retired:
            if not animations and not introduced:return retired
            # Changed terms can occupy the very space being vacated. Retire
            # that ink before preparing the next phase; prebuilt FadeIns paint
            # future destinations when nested groups set themselves up.
            return [Succession(AnimationGroup(*retired,run_time=.25),
                               DeferredAnimation(arrival,run_time=.75))]
        if moving and introduced:return [arrival()]
        animations.extend(FadeIn(part) for part in introduced)
        return animations

    def commit(self, target, scene):
        """Adopt the exact native layout, preserving unchanged term owners."""
        old_family = list(self.get_family())
        scene.remove(*old_family, *target.get_family())
        self.adopt_layout(target)
        scene.add(self)
        if hasattr(scene,'_capture_review_snapshot'): scene._capture_review_snapshot()

    def adopt_layout(self, target):
        """Adopt detached artwork without adding it to a scene.

        Layout transitions use this when introducing a new equation. ``commit``
        additionally consolidates ownership of an already animated equation.
        """
        from ..semantics import copy_semantics
        old = self.parts.copy()
        adopted = {}
        for name,new in target.parts.items():
            part = old.get(name, new)
            if part is not new:
                part.become(new)
                part.submobjects = [child.copy() for child in new.submobjects]
            part._algovis_label = target.slot_tex[name]
            part.tex_string = target.slot_tex[name]
            copy_semantics(new,part)
            if part.height>0:
                part.initial_height = part.height/(target.font_size*SCALE_FACTOR_PER_FONT_POINT)
            adopted[name] = part
        self.parts = adopted; self.slot_tex = target.slot_tex.copy()
        self._axis_origin = target._axis_origin.copy()
        direction=target._axis_unit.get_center()-target._axis_origin.get_center()
        direction=direction/np.linalg.norm(direction)
        self._axis_unit = VectorizedPoint(self._axis_origin.get_center()+direction*.01)
        self.submobjects = [*adopted.values(),self._axis_origin,self._axis_unit]
        self._native_size = target.font_size
        self._remember_layout()
        self._algovis_label = ''.join(self.slot_tex.values())
        self.tex_string = self._algovis_label
        # Transfers are instructions for this transition, not persistent
        # content. A later scene may reuse this live equation after the source
        # was retired; its already-arrived terms must not fly in a second time.
        self._copy_sources = {}
        copy_semantics(target,self)
        if hasattr(target, '_sum_contract'): self._sum_contract = target._sum_contract
        if getattr(self, '_algovis_typography_group', None):
            from ..layout import LessonStyle
            LessonStyle._watch_type(self,self._algovis_typography_group,
                                    getattr(self,'_algovis_type_role','equation'))
        return self

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
