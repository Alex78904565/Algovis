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
