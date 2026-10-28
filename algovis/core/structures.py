from manim import *
import enum
import math
from dataclasses import dataclass

from ..theme import DEFAULT_THEME
from ..semantics import SemanticProperties, set_semantics, copy_semantics


@dataclass(frozen=True)
class StateCellStyle:
    """The shared frame geometry for array entries and recursive call nodes."""
    corner_radius: float = .07
    stroke_width: float = 2.2
    fill_opacity: float = .94
    horizontal_padding: float = .16


DEFAULT_STATE_CELL_STYLE = StateCellStyle()


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

    def __init__(self, value, *, width=1.06, height=.78, value_scale=.64,
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
        self.label = value if isinstance(value,Mobject) else MathTex(str(value), color=theme.foreground).scale(value_scale)
        if self.label.width > width-self.frame_style.horizontal_padding:
            raise ValueError("StateCell value exceeds its width; reserve a wider cell")
        self.label.move_to(self.box)
        self._value_font_size=float(getattr(self.label,'font_size',48*value_scale)) if self.label.height>0 else 48*value_scale
        self._initial_box_height=float(self.box.height)
        super().__init__(self.box, self.label, **kwargs)
        if semantics is None and (color is None or status is not None or evaluation is not None):
            semantics=SemanticProperties(role,status,evaluation)
        if semantics is not None:
            set_semantics(self,semantics,theme=theme,part='box',channel='stroke')

    def populate(self,value,*,status='computed',evaluation=None):
        """Plan value entry and its status together; live content stays untouched."""
        target=self.copy()
        label=MathTex(str(value),font_size=self._value_font_size*self.box.height/self._initial_box_height,
                      color=self.theme.foreground).move_to(target.box)
        if label.width>target.box.width-self.frame_style.horizontal_padding*self.box.height/self._initial_box_height:
            raise ValueError('Value exceeds the cell; reserve a wider cell')
        target.label.become(label);target.label.tex_string=str(value)
        # Manim's become adopts geometry, not the TeX font reference. An
        # initially empty label has a zero reference height; retain the new
        # reference so later scaling and reviewer measurements stay finite.
        target.label.initial_height=label.initial_height
        properties=getattr(self,'semantics',SemanticProperties(role='current'))
        changes={'status':status}
        if evaluation is not None:changes['evaluation']=evaluation
        set_semantics(target,properties,theme=self.theme,part='box',channel='stroke',**changes)
        return _CellPopulation(self,target,str(value))


class _CellPopulation(Transform):
    def __init__(self,cell,target,value):
        self.value=value
        super().__init__(cell,target)

    def finish(self):
        super().finish()
        cell=self.mobject
        cell.box,cell.label=cell[0],cell[1]
        cell.label.tex_string=self.value
        cell.label.initial_height=self.target_mobject.label.initial_height
        copy_semantics(self.target_mobject,cell)


class CallNode(StateCell):
    """A recursive-call state cell that grows around its existing math label."""

    def __init__(self,label,*,minimum_radius=.34,padding=.12,shape='square',
                 color=None,theme=DEFAULT_THEME,style=None,**kwargs):
        if shape not in ('square','circle'):
            raise ValueError('Call node shape must be square or circle')
        if 'semantics' not in kwargs and (color is None or color==theme.node):
            kwargs['semantics']=SemanticProperties(role='node')
        radius=max(minimum_radius,label.width/2+padding,label.height/2+padding)
        super().__init__(label,width=2*radius,height=2*radius,color=color or theme.node,
            theme=theme,style=style,frame_shape='box' if shape=='square' else 'circle',**kwargs)


class StateRow(VGroup):
    """A row of the standard cells, with room for a plus or short arrow."""

    def __init__(self, values, *, gap=.42, theme=DEFAULT_THEME, cell_type=StateCell, **cell_options):
        super().__init__(*[cell_type(value, theme=theme, **cell_options)
                           for value in values])
        self.arrange(RIGHT, buff=gap)


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
