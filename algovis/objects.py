"""Content objects declare meaning; their scenes assign typography and layout."""
from manim import Text
from .core.math_row import MathRow
from .layout import LessonTypography
from .semantics import SemanticProperties,set_semantics,copy_semantics
from .theme import DEFAULT_THEME


class TextObject(Text):
    def __init__(self,text,*,type_role='body',role='neutral',status=None,evaluation=None,
                 theme=DEFAULT_THEME):
        options={'font':theme.text_font} if theme.text_font else {}
        super().__init__(text,font_size=LessonTypography().size(type_role),
                         color=theme.foreground,**options)
        self._algovis_type_role=type_role
        self._algovis_source_text=str(text)
        set_semantics(self,SemanticProperties(role,status,evaluation),theme=theme)


class Equation(MathRow):
    def __init__(self,parts,*,roles=None,role='neutral',status=None,evaluation=None,
                 theme=DEFAULT_THEME):
        from .composition import SlideObject
        sources={key:value for key,value in parts.items() if isinstance(value,SlideObject)}
        values={key:(value.tex if key in sources else value) for key,value in parts.items()}
        super().__init__(values,color=theme.foreground)
        self._copy_sources=sources
        self._algovis_type_role='equation'
        set_semantics(self,SemanticProperties(role,status,evaluation),theme=theme)
        for key,source in sources.items():
            from .composition import PlannedPart
            copy_semantics(source if isinstance(source,PlannedPart) else source.mobject,self.part(key))
            if hasattr(self.part(key),'semantics'):set_semantics(self.part(key))
        for key,meaning in (roles or {}).items():
            properties=meaning if isinstance(meaning,SemanticProperties) else SemanticProperties(role=meaning)
            set_semantics(self.part(key),properties,theme=theme)

    def cancel(self,part,text):
        """Strike a unique run of literal algebraic symbols, then retire it."""
        from manim import Create,FadeOut,Line,Succession,VGroup,DL,UR
        source=self.slot_tex[part]
        if '\\' in source or '{' in source or source.count(text)!=1:
            raise ValueError('Literal cancellation needs a unique plain-symbol run')
        glyphs=[glyph for glyph in self.part(part).family_members_with_points()
                if not glyph.submobjects and glyph.get_fill_opacity()>.01]
        symbols=source.replace(' ','')
        if len(glyphs)!=len(symbols):raise ValueError('Cancellation glyphs do not match the declared literal symbols')
        start=symbols.index(text)
        selected=VGroup(*glyphs[start:start+len(text)])
        strike=Line(selected.get_corner(DL),selected.get_corner(UR),color=self._semantic_theme.danger,stroke_width=2)
        return Succession(Create(strike),FadeOut(strike))


class FunctionDefinition(Equation):
    """A named function and its English meaning, in one semantic equation.

    The function keeps the same paint whether this is a full-width definition
    or one side of a comparison. Wrapping belongs to this object, not the scene.
    """
    _algovis_content_fields=('_definition_text','_definition_call')

    def __init__(self,call,meaning,*,theme=DEFAULT_THEME):
        self._definition_text,self._definition_call=str(meaning),str(call)
        self._definition_theme=theme
        super().__init__({'call':str(call),'eq':'=','meaning':self._meaning_tex(72)},
                         roles={'call':'current'},theme=theme)

    def _meaning_tex(self,width):
        import textwrap
        lines=textwrap.wrap(self._definition_text,width=width,break_long_words=False)
        if not lines:return ''
        escaped=[line.replace('&',r'\&').replace('_',r'\_').replace('%',r'\%') for line in lines]
        return r'\begin{aligned}[t]'+r'\\'.join(r'&\text{'+line+'}' for line in escaped)+r'\end{aligned}'

    def layout_in(self,width,height,typography):
        center=self.get_center()
        for limit in range(72,20,-2):
            target=self.next_layout(meaning=self._meaning_tex(limit))
            if target.width<=width or limit==22:
                self.adopt_layout(target);self.move_to(center);break

    def with_state(self,*,call=None,meaning=None):
        return FunctionDefinition(call or self._definition_call,
            self._definition_text if meaning is None else meaning,theme=self._definition_theme).move_to(self)
