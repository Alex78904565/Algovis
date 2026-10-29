"""Proof compositions own their row alignment; scenes supply content and cues."""
import numpy as np
from manim import UP, RIGHT, Text, VectorizedPoint, VGroup, Transform

from ..frames import ProofFrame


def first_line_of(content):
    """Use the first explicit row of a stacked group, or a single formula."""
    if type(content) is VGroup and len(content):
        return first_line_of(content[0])
    if isinstance(content,Text) and '\n' in getattr(content,'original_text',content.text):
        glyphs=[g for g in content.submobjects if g.has_points() and g.height>0]
        if glyphs:
            highest=max(g.get_y() for g in glyphs)
            threshold=highest-float(np.median([g.height for g in glyphs]))*.85
            return VGroup(*[g for g in glyphs if g.get_y()>=threshold])
    return content


def _follow_first_line(label, dt=0):
    reference = getattr(label, '_proof_first_line', None)
    if reference is not None:
        label.align_to(reference, UP)


def bind_proof_label(label, content, first_line=None):
    """Bind an existing label without changing or adopting its content."""
    label._proof_first_line = first_line if first_line is not None else first_line_of(content)
    if _follow_first_line not in label.updaters:
        label.add_updater(_follow_first_line)
    _follow_first_line(label)
    return label


class ProofLabelAlignment(Transform):
    """Adopt a new first-line constraint on the same cue as its row change."""
    def __init__(self,label,content,first_line=None,**kwargs):
        self.content=content
        self.first_line=first_line if first_line is not None else first_line_of(content)
        target=label.copy().clear_updaters().align_to(self.first_line,UP)
        super().__init__(label,target,**kwargs)

    def finish(self):
        super().finish()
        bind_proof_label(self.mobject,self.content,self.first_line)


class ProofRow(VGroup):
    """A row label follows the first line, including after group transforms."""
    def __init__(self,label,content,*,first_line=None,**kwargs):
        self.label,self.content=label,content
        super().__init__(label,content,**kwargs)
        bind_proof_label(label,content,first_line)


class Proof(VGroup):
    """A reusable proof with named rows and one shared layout strategy.

    Build a complete proof before revealing it with ``add_row``. For progressive
    narration, ``scene.proof_row_on_cue`` adds a row only at its spoken cue.
    Mathematical content is never independently shrunk to fit its slot.
    """
    def __init__(self,profile='compact',*,theme=None,style=None,**kwargs):
        options={'style':style}
        if theme is not None:options['theme']=theme
        self.frame=ProofFrame(profile,**options)
        self.rows_by_name={}
        self.pending_labels=self.frame.labels
        self.rows=VGroup()
        self._layout_origin=VectorizedPoint()
        self._layout_x=VectorizedPoint(RIGHT)
        self._layout_y=VectorizedPoint(UP)
        super().__init__(self.frame.divider,self.pending_labels,self.rows,
                         self._layout_origin,self._layout_x,self._layout_y,**kwargs)

    def prepare_content(self,name,content):
        """Lay out new content in the proof's current translated/scaled frame."""
        origin=self._layout_origin.get_center()
        x=self._layout_x.get_center()-origin;y=self._layout_y.get_center()-origin
        if not np.isclose(np.linalg.norm(x),np.linalg.norm(y)):
            raise ValueError('Proof layout requires uniform scaling')
        content.scale(float(np.linalg.norm(x)))
        content.move_to(self.anchor(name),aligned_edge=-RIGHT)
        return content

    def anchor(self,name):
        origin=self._layout_origin.get_center()
        x=self._layout_x.get_center()-origin;y=self._layout_y.get_center()-origin
        local=self.frame.anchor(name)
        return origin+x*local[0]+y*local[1]

    def add_row(self,name,content,*,first_line=None):
        key=str(name).upper().replace('_',' ')
        if key in self.rows_by_name:
            raise ValueError('Use a row change for an existing proof row')
        self.prepare_content(key,content)
        label=self.frame.labels_by_name[key]
        self.pending_labels.remove(label)
        row=ProofRow(label,content,first_line=first_line)
        self.rows_by_name[key]=row;self.rows.add(row)
        return row

    def adopt_row(self,name,content,*,first_line=None):
        row=self.row(name)
        row.content=content
        row.submobjects=[row.label,content]
        bind_proof_label(row.label,content,first_line)
        return row

    def consolidate(self,scene):
        """Restore one visible owner after Manim animates nested content."""
        scene.remove(*self.get_family())
        scene.add(self)

    def row(self,name):
        return self.rows_by_name[str(name).upper().replace('_',' ')]
