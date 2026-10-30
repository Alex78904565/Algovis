from manim import *
import enum
import math
import numpy as np
from dataclasses import dataclass

from ..theme import DEFAULT_THEME
from ..semantics import SemanticProperties, set_semantics, copy_semantics
from ..layout import LessonTypography, LessonStyle, measured_font_size


@dataclass(frozen=True)
class StateCellStyle:
    """The shared frame geometry for array entries and recursive call nodes."""
    corner_radius: float = .07
    stroke_width: float = 2.2
    fill_opacity: float = .94
    horizontal_padding: float = .16
    semantic_fill_strength: float = 0.

    def __post_init__(self):
        if not math.isfinite(self.semantic_fill_strength) or not 0<=self.semantic_fill_strength<=1:
            raise ValueError('Semantic fill strength must be between zero and one')


DEFAULT_STATE_CELL_STYLE = StateCellStyle()
INDUCTION_STATE_CELL_STYLE = StateCellStyle(semantic_fill_strength=.3)


class CellState(enum.Enum):
    UNSEEN = "unseen"
    ACTIVE = "active"
    RESOLVED = "resolved"
    CHOSEN = "chosen"


class StateCell(VGroup):
    """The standard separated state/value cell used throughout a lesson.

    Keep the box and label independently addressable for staged population.
    Scale a whole row for a miniature recap; do not invent a second cell style.
    ``color`` controls the border, while the value keeps its neutral ink.
    """

    def __init__(self, value, *, width=1.06, height=.78, value_scale=None,
                 color=None, theme=DEFAULT_THEME, style=None, frame_shape='box',
                 semantics=None, role='current',status=None,evaluation=None, **kwargs):
        self.theme = theme
        self.frame_style = style or DEFAULT_STATE_CELL_STYLE
        if frame_shape not in ('box','circle'):
            raise ValueError('State frame shape must be box or circle')
        if frame_shape=='box':
            self.box = RoundedRectangle(width=width,height=height,
                corner_radius=min(self.frame_style.corner_radius,min(width,height)/2),
                stroke_color=color or theme.primary,stroke_width=self.frame_style.stroke_width,
                fill_color=theme.background,fill_opacity=self.frame_style.fill_opacity)
        else:
            self.box = Circle(radius=width/2,stroke_color=color or theme.primary,
                stroke_width=self.frame_style.stroke_width,fill_color=theme.background,
                fill_opacity=self.frame_style.fill_opacity)
        value_size=LessonTypography().equation if value_scale is None else 48*value_scale
        self.label = value if isinstance(value,Mobject) else MathTex(str(value),font_size=value_size,color=theme.foreground)
        self.label._algovis_empty_font_size=value_size
        if self.label.width > width-self.frame_style.horizontal_padding+1e-7:
            raise ValueError("StateCell value exceeds its width; reserve a wider cell")
        self.label.move_to(self.box)
        self._value_font_size=float(getattr(self.label,'font_size',value_size)) if self.label.height>0 else value_size
        self._initial_box_height=float(self.box.height)
        super().__init__(self.box, self.label, **kwargs)
        if semantics is None and (color is None or status is not None or evaluation is not None):
            semantics=SemanticProperties(role,status,evaluation)
        if semantics is not None:
            set_semantics(self,semantics,theme=theme,part='box',channel='stroke')

    def apply_semantic_paint(self,properties,theme,*,part,channel):
        """Tint the owned frame while preserving neutral, readable label ink.

        Blend an opaque background rather than making edges behind a tree node
        visible through a translucent status overlay. Ordinary cells retain
        their existing fill unless their style opts into semantic tinting.
        """
        strength=self.frame_style.semantic_fill_strength
        if strength and part=='box' and channel=='stroke':
            colored=properties.status not in (None,'unseen') or properties.evaluation is not None
            color=interpolate_color(ManimColor(theme.background),ManimColor(properties.color(theme)),strength if colored else 0)
            self.box.set_fill(color,opacity=self.frame_style.fill_opacity)

    def apply_scene_typography(self,typography,*,group):
        # A cell owns the relationship between its frame and its label. It
        # receives a scene type role without scaling a lone glyph independently
        # of the component's population policy.
        role='label' if isinstance(self,CallNode) else 'equation'
        size=float(measured_font_size(self.label) or 0)
        desired=typography.size(role)
        if size>0 and self.label.height>0:
            self.label.scale(desired/size).move_to(self.box)
            if self.label.width>self.box.width-self.frame_style.horizontal_padding+1e-7:
                raise ValueError('Cell text exceeds its component; reserve a wider cell')
        self.label._algovis_empty_font_size=desired
        self._value_font_size=desired*self._initial_box_height/self.box.height
        LessonStyle._watch_type(self.label,group+'/cells',role)

    def connection_point(self,direction):
        """Intersect a center ray with the frame, rather than its support corner."""
        delta=np.asarray(direction,dtype=float)
        radii=np.array([self.box.width/2,self.box.height/2])
        if np.linalg.norm(delta[:2])<1e-10:return self.box.get_center()
        if isinstance(self.box,Circle):
            distance=1/np.linalg.norm(delta[:2]/radii)
        else:
            distance=min(radii[i]/abs(delta[i]) for i in (0,1) if abs(delta[i])>1e-10)
        return self.box.get_center()+distance*delta

    def populate(self,value,*,status='computed',evaluation=None):
        """Plan value entry and its status together; live content stays untouched."""
        target=self.copy()
        label=MathTex(str(value),font_size=self._value_font_size*self.box.height/self._initial_box_height,
                      color=self.theme.foreground).move_to(target.box)
        if label.width>target.box.width-self.frame_style.horizontal_padding*self.box.height/self._initial_box_height+1e-7:
            raise ValueError('Value exceeds the cell; reserve a wider cell')
        target.label=label
        target.submobjects[1]=label
        # Manim's become adopts geometry, not the TeX font reference. An
        # initially empty label has a zero reference height; retain the new
        # reference so later scaling and reviewer measurements stay finite.
        target.label.initial_height=label.initial_height
        properties=getattr(self,'semantics',SemanticProperties(role='current'))
        changes={'status':status}
        if evaluation is not None:changes['evaluation']=evaluation
        set_semantics(target,properties,theme=self.theme,part='box',channel='stroke',**changes)
        return _CellPopulation(self,target,str(value))

    def adopt_layout(self,target):
        """Retain the cell and label identities, discard transform padding."""
        self.box.become(target.box)
        self.label.become(target.label)
        self.label.points=target.label.points.copy()
        self.label.submobjects=[part.copy() for part in target.label.submobjects]
        for field in ('tex_string','initial_height','_font_size','_algovis_empty_font_size'):
            if hasattr(target.label,field):setattr(self.label,field,getattr(target.label,field))
        self._value_font_size=target._value_font_size
        self._initial_box_height=target._initial_box_height
        self.submobjects=[self.box,self.label]
        copy_semantics(target,self)
        group=getattr(target.label,'_algovis_typography_group',
                      getattr(self.label,'_algovis_typography_group',None))
        if group:
            LessonStyle._watch_type(self.label,group,
                getattr(target.label,'_algovis_type_role',getattr(self.label,'_algovis_type_role','equation')))
        return self

    def motions_to(self,target):
        class CellMove(Transform):
            def finish(motion):
                super().finish()
                motion.mobject.adopt_layout(motion.target_mobject)
        return [CellMove(self,target)]


class _CellPopulation(Animation):
    """Reveal a value at its cell centre; never morph an empty SVG into it."""
    def __init__(self,cell,target,value):
        self.value=value
        self.target_mobject=target
        self.canonical_label=target.label.copy()
        self.entering_label=target.label.copy()
        self.retiring_label=cell.label.copy()
        self.process=AnimationGroup(Transform(cell.box,target.box),
            FadeOut(self.retiring_label),FadeIn(self.entering_label),lag_ratio=0)
        self.animations=self.process.animations
        self.host_scene=None
        super().__init__(cell)

    def _setup_scene(self,scene):
        self.host_scene=scene
        self.process._setup_scene(scene)

    def begin(self):
        self.mobject.label.set_opacity(0)
        self.process.begin()

    def interpolate(self,alpha):
        self.process.interpolate(alpha)

    def finish(self):
        self.process.finish()
        cell=self.mobject;label=self.canonical_label
        # Keep the value slot's identity, with exactly the new glyphs. Temporary
        # local fades never change its geometry or move numbers across the row.
        cell.label.points=label.points.copy()
        cell.label.submobjects=[part.copy() for part in label.submobjects]
        cell.label.tex_string=self.value
        cell.label.initial_height=label.initial_height
        cell.label._font_size=label._font_size
        cell.label.set_fill(label.get_fill_color(),opacity=1)
        if getattr(cell.label,'_algovis_typography_group',None):
            LessonStyle._watch_type(cell.label,cell.label._algovis_typography_group,
                                    cell.label._algovis_type_role)
        copy_semantics(self.target_mobject,cell)
        if self.host_scene is not None:
            self.host_scene.remove(*self.entering_label.get_family(),*self.retiring_label.get_family())

    def clean_up_from_scene(self,scene):
        self.process.clean_up_from_scene(scene)
        scene.remove(*self.entering_label.get_family(),*self.retiring_label.get_family())
        super().clean_up_from_scene(scene)


class CallNode(StateCell):
    """A recursive-call state cell that grows around its existing math label."""

    def __init__(self,label,*,minimum_radius=.34,padding=.12,shape='square',
                 color=None,theme=DEFAULT_THEME,style=None,**kwargs):
        if shape not in ('square','circle','box'):
            raise ValueError('Call node shape must be square, box or circle')
        if 'semantics' not in kwargs and (color is None or color==theme.node):
            kwargs['semantics']=SemanticProperties(role='node')
        radius=max(minimum_radius,label.width/2+padding,label.height/2+padding)
        height=2*max(minimum_radius,label.height/2+padding) if shape=='box' else 2*radius
        super().__init__(label,width=2*radius,height=height,color=color or theme.node,
            theme=theme,style=style,frame_shape='box' if shape in ('square','box') else 'circle',**kwargs)


class StateRow(VGroup):
    """A row of the standard cells, with room for a plus or short arrow."""

    def __init__(self, values, *, gap=.42, theme=DEFAULT_THEME, cell_type=StateCell, **cell_options):
        self.gap=gap
        super().__init__(*[cell_type(value, theme=theme, **cell_options)
                           for value in values])
        self.arrange(RIGHT, buff=gap)

    def apply_scene_typography(self,typography,*,group):
        center=self.get_center()
        for cell in self:cell.apply_scene_typography(typography,group=group)
        self.arrange(RIGHT,buff=self.gap).move_to(center)

    def adopt_layout(self,target):
        if len(self)!=len(target):raise ValueError('Changing a state row length requires an explicit row model')
        for cell,destination in zip(self,target):cell.adopt_layout(destination)
        self.gap=target.gap
        return self


class DPTable(VGroup):
    """An indexed, value-aware dynamic-programming table."""

    def __init__(self, rows, cols, cell_width=1.0, cell_height=0.6,
                 row_labels=None, col_labels=None, values=None,
                 label_scale=0.48, value_scale=0.52,
                 theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        self.cell_styles = {
            CellState.UNSEEN: (theme.foreground, 0.0, 1.0),
            CellState.ACTIVE: (theme.accent, 0.20, 3.0),
            CellState.RESOLVED: (theme.success, 0.16, 2.0),
            CellState.CHOSEN: (theme.primary, 0.32, 3.5),
        }
        self.rows = rows
        self.cols = cols
        self.grid = VGroup()
        self.values = {}
        self.value_mobjects = VGroup()
        self.dependency_arrows = VGroup()
        self.index_labels = VGroup()
        self.cell_states = {(r, c): CellState.UNSEEN for r in range(rows) for c in range(cols)}
        self._value_scale = value_scale

        for _r in range(rows):
            row = VGroup(*[
                Rectangle(width=cell_width, height=cell_height,
                          stroke_width=1.4, stroke_color=theme.muted)
                for _c in range(cols)
            ]).arrange(RIGHT, buff=0)
            self.grid.add(row)
        self.grid.arrange(DOWN, buff=0)
        self.add(self.grid, self.value_mobjects, self.dependency_arrows, self.index_labels)

        if row_labels is not None:
            for r, value in enumerate(row_labels):
                label = self._make_label(value, label_scale)
                label.next_to(self.get_cell(r, 0), LEFT, buff=0.16)
                self.index_labels.add(label)
        if col_labels is not None:
            for c, value in enumerate(col_labels):
                label = self._make_label(value, label_scale)
                label.next_to(self.get_cell(0, c), UP, buff=0.14)
                self.index_labels.add(label)
        if values is not None:
            for r, row in enumerate(values):
                for c, value in enumerate(row):
                    if value is not None:
                        self.set_value(r, c, value)

    @staticmethod
    def _make_label(value, scale):
        return value if isinstance(value, Mobject) else MathTex(str(value)).scale(scale)

    def get_cell(self, r, c):
        return self.grid[r][c]

    def get_entry(self, r, c):
        return self.values.get((r, c))

    def set_value(self, r, c, value, color=None):
        color = color or self.theme.foreground
        old = self.values.get((r, c))
        if old is not None:
            self.value_mobjects.remove(old)
        mob = self._make_label(value, self._value_scale).set_color(color)
        mob.move_to(self.get_cell(r, c))
        self.values[(r, c)] = mob
        self.value_mobjects.add(mob)
        return mob

    def write_value(self, r, c, value, color=None, replace=True):
        color = color or self.theme.foreground
        old = self.values.get((r, c))
        mob = self._make_label(value, self._value_scale).set_color(color)
        mob.move_to(self.get_cell(r, c))
        self.values[(r, c)] = mob
        if old is not None and replace:
            self.value_mobjects.remove(old)
            self.value_mobjects.add(mob)
            return ReplacementTransform(old, mob)
        self.value_mobjects.add(mob)
        return FadeIn(mob, scale=0.8)

    def set_cell_state(self, r, c, state):
        if isinstance(state, str):
            state = CellState(state)
        self.cell_states[(r, c)] = state
        color, opacity, width = self.cell_styles[state]
        return self.get_cell(r, c).animate.set_stroke(color, width=width).set_fill(color, opacity=opacity)

    def highlight_dependency(self, target_cell, dep_cells, color=None, labels=None):
        color = color or self.theme.accent
        arrows = VGroup()
        for index, dep in enumerate(dep_cells):
            arrow = Arrow(dep.get_center(), target_cell.get_center(), buff=0.13,
                          color=color, stroke_width=2)
            if labels and index < len(labels) and labels[index] is not None:
                tag = self._make_label(labels[index], 0.38).set_color(color)
                tag.next_to(arrow.get_center(), UP, buff=0.04)
                arrows.add(VGroup(arrow, tag))
            else:
                arrows.add(arrow)
        self.dependency_arrows.add(*arrows)
        return Create(arrows)

    def clear_dependencies(self):
        old = self.dependency_arrows
        self.dependency_arrows = VGroup()
        return FadeOut(old)

    def populate(self, order, value_fn, run_time=0.45, active_color=None):
        """Fill cells in order; value_fn receives (row, column, table)."""
        active_color = active_color or self.theme.accent
        steps = []
        for r, c in order:
            value = value_fn(r, c, self)
            steps.append(AnimationGroup(
                self.set_cell_state(r, c, CellState.ACTIVE),
                self.write_value(r, c, value, color=active_color),
            ))
            steps.append(self.set_cell_state(r, c, CellState.RESOLVED))
        return Succession(*steps, run_time=run_time * max(1, len(steps)))

    def traceback(self, path, color=None, run_time=0.35):
        """Highlight a recovered solution path through (row, column) cells."""
        color = color or self.theme.primary
        steps = []
        for previous, current in zip(path, path[1:]):
            pr, pc = previous
            cr, cc = current
            connector = Arrow(self.get_cell(pr, pc).get_center(),
                              self.get_cell(cr, cc).get_center(), buff=0.14,
                              color=color, stroke_width=3)
            self.dependency_arrows.add(connector)
            steps.append(AnimationGroup(
                self.set_cell_state(pr, pc, CellState.CHOSEN), Create(connector)
            ))
        if path:
            steps.append(self.set_cell_state(*path[-1], CellState.CHOSEN))
        return Succession(*steps, run_time=run_time * max(1, len(steps)))


class DPWorkflow:
    """Coordinate table population, traceback, and optional pseudocode."""

    def __init__(self, table, code=None):
        self.table = table
        self.code = code

    def population_animation(self, steps, run_time=0.65):
        animations = []
        for step in steps:
            r, c = step["cell"]
            begin = [self.table.set_cell_state(r, c, CellState.ACTIVE)]
            if self.code is not None and "code_line" in step:
                begin.append(self.code.highlight_line(step["code_line"]))
            deps = step.get("dependencies", [])
            if deps:
                begin.append(self.table.highlight_dependency(
                    self.table.get_cell(r, c),
                    [self.table.get_cell(*coord) for coord in deps],
                    labels=step.get("dependency_labels"),
                ))
            animations.append(AnimationGroup(*begin))
            animations.append(AnimationGroup(
                self.table.write_value(r, c, step["value"]),
                self.table.set_cell_state(r, c, CellState.RESOLVED),
            ))
        return Succession(*animations, run_time=run_time * max(1, len(animations)))

    def recovery_animation(self, path, code_line=None, run_time=0.4):
        parts = [self.table.traceback(path, run_time=run_time)]
        if self.code is not None and code_line is not None:
            parts.append(self.code.highlight_line(code_line))
        return AnimationGroup(*parts)


class HashTable(VGroup):
    def __init__(self, size, width=1.5, height=0.5, **kwargs):
        super().__init__(**kwargs)
        self.buckets = VGroup()
        self.entries = {}
        for i in range(size):
            bucket = Rectangle(width=width, height=height)
            label = Tex(str(i)).scale(0.5).next_to(bucket, LEFT)
            self.buckets.add(VGroup(bucket, label))
        self.buckets.arrange(DOWN, buff=0.1)
        self.add(self.buckets)

    def add_key(self, index, key_tex):
        key = MathTex(key_tex).scale(0.6).move_to(self.buckets[index][0])
        self.entries[index] = key
        self.add(key)
        return FadeIn(key)


class GraphVis(VGroup):
    """A state-aware weighted graph with automatic or explicit placement."""

    def __init__(self, nodes_dict, edges_list, directed=False, edge_weights=None,
                 layout="circular", radius=2.0, node_radius=0.3, **kwargs):
        super().__init__(**kwargs)
        names = list(nodes_dict) if isinstance(nodes_dict, dict) else list(nodes_dict)
        explicit = isinstance(nodes_dict, dict) and all(v is not None for v in nodes_dict.values())
        positions = nodes_dict if explicit else self._layout_positions(names, layout, radius)
        self.nodes = {}
        self.node_states = {name: "unseen" for name in names}
        self.node_group = VGroup()
        self.edges = VGroup()
        self.edge_map = {}
        self.weight_labels = VGroup()
        self.directed = directed

        for name in names:
            shape = Circle(radius=node_radius, color=WHITE).set_fill(BLACK, opacity=0.9)
            label = MathTex(str(name)).scale(0.55)
            node = VGroup(shape, label).move_to(positions[name])
            node.shape = shape
            self.nodes[name] = node
            self.node_group.add(node)

        for data in edges_list:
            u, v = data[:2]
            weight = data[2] if len(data) > 2 else (edge_weights or {}).get((u, v))
            delta = self.nodes[v].get_center() - self.nodes[u].get_center()
            start = self.nodes[u].shape.get_boundary_point(delta)
            end = self.nodes[v].shape.get_boundary_point(-delta)
            edge = (Arrow(start, end, buff=0.02, max_tip_length_to_length_ratio=0.12)
                    if directed else Line(start, end))
            edge.set_color(GREY_B).set_stroke(width=2)
            self.edges.add(edge)
            self.edge_map[(u, v)] = edge
            if not directed:
                self.edge_map[(v, u)] = edge
            if weight is not None:
                tag = MathTex(str(weight)).scale(0.43)
                normal = rotate_vector(delta / max(np.linalg.norm(delta), 1e-6), PI / 2)
                tag.move_to(edge.get_center() + normal * 0.14)
                tag.add_background_rectangle(color=BLACK, opacity=0.85, buff=0.03)
                self.weight_labels.add(tag)
        self.add(self.edges, self.weight_labels, self.node_group)

    @staticmethod
    def _layout_positions(names, layout, radius):
        count = max(1, len(names))
        if layout == "grid":
            cols = math.ceil(math.sqrt(count))
            return {name: np.array(((i % cols) * 1.4, -(i // cols) * 1.2, 0.0))
                    for i, name in enumerate(names)}
        return {name: radius * np.array((math.cos(PI / 2 - TAU * i / count),
                                         math.sin(PI / 2 - TAU * i / count), 0.0))
                for i, name in enumerate(names)}

    def set_node_state(self, name, state):
        styles = {"unseen": (WHITE, 0.0), "active": (YELLOW, 0.25),
                  "visited": (GREEN_B, 0.25), "chosen": (BLUE_B, 0.38)}
        color, opacity = styles[state]
        self.node_states[name] = state
        return self.nodes[name].shape.animate.set_color(color).set_fill(color, opacity=opacity)

    def highlight_edge(self, u, v, color=YELLOW, width=5):
        return self.edge_map[(u, v)].animate.set_color(color).set_stroke(width=width)

    def traverse_path(self, path, color=YELLOW, run_time=0.45, leave_visited=True):
        steps = []
        if path:
            steps.append(self.set_node_state(path[0], "active"))
        for u, v in zip(path, path[1:]):
            steps.append(AnimationGroup(
                self.highlight_edge(u, v, color=color),
                self.set_node_state(u, "visited" if leave_visited else "unseen"),
                self.set_node_state(v, "active"),
            ))
        if path:
            steps.append(self.set_node_state(path[-1], "chosen"))
        return Succession(*steps, run_time=run_time * max(1, len(steps)))

    def reset_states(self):
        animations = [self.set_node_state(name, "unseen") for name in self.nodes]
        animations += [edge.animate.set_color(GREY_B).set_stroke(width=2)
                       for edge in set(self.edge_map.values())]
        return AnimationGroup(*animations)
