from manim import *
import enum
import numpy as np

from ..theme import DEFAULT_THEME
from .structures import CallNode
from ..semantics import SemanticProperties, SemanticChange
from ..layout import LessonStyle, LessonTypography,measured_font_size
from ..utils.effects import DeferredAnimation

class NodeState(enum.Enum):
    PENDING = 1
    ACTIVE = 2
    RESOLVED = 3

class RecursiveTree(VGroup):
    """
    A tree that builds itself based on a recursive rule and tracks evaluation states.
    """
    def __init__(self, branching_fn, root_args, depth_limit=5, height=1.15,
                 width=1.15, node_radius=0.34, label_scale=None,
                 node_padding=0.12, node_factory=None, node_color=None,
                 state_key=None, level_fn=None, node_shape="circle",
                 node_style=None, node_type=CallNode,
                 reveal_depth=None,
                 backbone_space=False,
                 profile='standard',
                 theme=DEFAULT_THEME,
                 **kwargs):
        super().__init__(**kwargs)
        if profile not in ('standard','compact'):raise ValueError('Unknown tree profile')
        if profile=='compact':
            width,height,node_radius,node_padding,node_shape=1.,.7,.20,.08,'box'
        self.profile=profile
        self.theme = theme
        self.branching_fn = branching_fn
        self.depth_limit = depth_limit
        # ``width`` and ``height`` are geometry properties owned by Manim.
        # Keep layout spacing under distinct names or all nodes collapse.
        self.level_spacing = height
        self.sibling_spacing = width
        self.node_radius = node_radius
        self.label_scale = label_scale
        self.node_padding = node_padding
        self.node_factory = node_factory
        self.node_color = node_color or theme.node
        self.node_shape = node_shape
        self.node_style = node_style
        self.node_type = node_type
        self.reveal_depth=reveal_depth
        self.backbone_space=backbone_space
        self.state_key = state_key or (lambda args: tuple(args))
        self.level_fn = level_fn
        self.memoized_graph = None
        self.nodes = VGroup()
        self.edges = VGroup()

        # Build hierarchy tree data structure
        self.tree_structure = self._build_node_data(root_args, 0)

        # A fixed center-to-center gap works only while every node has roughly
        # the same small label.  State-heavy labels (notably TSP visit bits)
        # make square nodes taller, so derive a safe center position for each
        # layer from the actual rendered node heights.
        level_heights = {}
        def measure_levels(node_data, depth):
            display_level = self._display_level(node_data, depth)
            level_heights[display_level] = max(
                level_heights.get(display_level, 0),
                node_data["mobject"].height,
            )
            for child in node_data["children"]:
                measure_levels(child, depth + 1)
        measure_levels(self.tree_structure, 0)
        self.level_y_positions = {0: 0.0}
        for depth in range(1, max(level_heights, default=0) + 1):
            minimum_spacing = (
                level_heights[depth - 1] / 2
                + level_heights[depth] / 2
                + 0.16
            )
            center_spacing = max(self.level_spacing, minimum_spacing)
            self.level_y_positions[depth] = (
                self.level_y_positions[depth - 1] - center_spacing
            )

        # Position nodes relative to root at (0, 0, 0)
        self._position_nodes(self.tree_structure, x=0, depth=0)

        # Draw edges first, then nodes, so lines never cut through circles/text.
        self._create_edges(self.tree_structure)
        self.add(self.edges, self.nodes)
        if backbone_space:
            self.backbone_anchor=VectorizedPoint(self._backbone_tail_position())
            self.add(self.backbone_anchor)

    def _backbone_tail_position(self):
        chain=[];cursor=self.tree_structure
        while True:
            chain.append(cursor)
            if not cursor['children']:break
            cursor=cursor['children'][0]
        if len(chain)<2:return chain[-1]['mobject'].get_center()
        a,b=(node['mobject'].get_center() for node in chain[-2:])
        return b+(b-a)

    def _build_node_data(self, args, depth):
        label_str, child_args = self.branching_fn(*args)

        size=LessonTypography().label if self.label_scale is None else 48*self.label_scale
        label = MathTex(label_str,font_size=size,color=self.theme.foreground)
        label._algovis_empty_font_size=size
        if self.node_factory is None:
            # Fixed-radius nodes clipped wider labels such as f(12).  Treat the
            # configured radius as a minimum and grow to fit the rendered label.
            node_mobject=self.node_type(label,minimum_radius=self.node_radius,
                padding=self.node_padding,shape=self.node_shape,color=self.node_color,
                theme=self.theme,style=self.node_style)
            node_shape=node_mobject.box
        else:
            node_shape = self.node_factory(label_str, label)
            node_mobject = VGroup(node_shape, label)
            # Custom artwork keeps the same frame-only semantic binding.
            node_mobject.box = node_shape
            node_mobject.label = label

        self.nodes.add(node_mobject)

        node_data = {
            "args": args,
            "mobject": node_mobject,
            # Keep ``circle`` as a compatibility alias for existing scenes.
            "circle": node_shape,
            "shape": node_shape,
            "label": label,
            "state": NodeState.PENDING,
            "children": [],
            "edges": []
        }

        if depth < self.depth_limit and child_args:
            for c_args in child_args:
                child_data = self._build_node_data(c_args, depth + 1)
                node_data["children"].append(child_data)

        return node_data

    def apply_scene_typography(self,typography,*,group):
        """The tree reflows its boxes and edges when its label role changes."""
        if hasattr(self,'leaf_numbers'):
            for label in self.leaf_numbers:
                label.scale(typography.label/label.font_size)
                LessonStyle._watch_type(label,group+'/leaf-counts','label')
        if all(abs(float(measured_font_size(data['label']))-typography.label)<1e-6 for data,_ in self.iter_nodes()):
            for data,_ in self.iter_nodes():LessonStyle._watch_type(data['label'],group+'/tree-labels','label')
            return
        center=self.get_center()
        edge_opacities=[edge.get_stroke_opacity() for edge in self.edges]
        for data,_ in self.iter_nodes():
            label=data['label'];current=float(measured_font_size(label))
            if current>0 and label.height>0:label.scale(typography.label/current)
            if self.node_factory is None:
                radius=max(self.node_radius,label.width/2+self.node_padding,
                           label.height/2+self.node_padding)
                box=data['shape'];box.stretch_to_fit_width(2*radius)
                box.stretch_to_fit_height(2*max(self.node_radius,label.height/2+self.node_padding)
                                          if self.node_shape=='box' else 2*radius)
                label.move_to(box)
            LessonStyle._watch_type(label,group+'/tree-labels','label')
        heights={}
        for data,depth in self.iter_nodes():
            level=self._display_level(data,depth)
            heights[level]=max(heights.get(level,0),data['mobject'].height)
            data['edges']=[]
        self.level_y_positions={0:0.}
        for depth in range(1,max(heights,default=0)+1):
            self.level_y_positions[depth]=self.level_y_positions[depth-1]-max(
                self.level_spacing,heights.get(depth-1,0)/2+heights.get(depth,0)/2+.16)
        self._position_nodes(self.tree_structure,x=0,depth=0)
        self.edges.submobjects=[]
        self._create_edges(self.tree_structure)
        for edge,opacity in zip(self.edges,edge_opacities):edge.set_stroke(opacity=opacity)
        self.move_to(center)
        self._arrange_attachments()

    def enter_animation(self):
        if self.reveal_depth is None:return FadeIn(self)
        self.prepare_layered_unroll()
        return self.get_depth_reveal_anim(0,self.reveal_depth)

    def layout_in(self,width,height,typography):
        """Use available scene space before shrinking the complete diagram."""
        center=self.get_center()
        layers=self.get_layers()
        leaves=sum(not data['children'] for data,_ in self.iter_nodes())
        self.sibling_spacing=min(self.sibling_spacing,width/max(1,leaves))
        largest=max(data['mobject'].height for data,_ in self.iter_nodes())
        levels=max((self._display_level(data,depth) for data,depth in self.iter_nodes()),default=0)
        if self.backbone_space:levels+=1
        self.level_spacing=min(self.level_spacing,max(.1,(height-largest)/max(1,levels)))
        heights={}
        opacities=[edge.get_stroke_opacity() for edge in self.edges]
        for data,depth in self.iter_nodes():
            level=self._display_level(data,depth)
            heights[level]=max(heights.get(level,0),data['mobject'].height)
            data['edges']=[]
        self.level_y_positions={0:0.}
        for level in range(1,levels+1):
            gap=max(self.level_spacing,heights.get(level-1,0)/2+heights.get(level,0)/2+.16)
            self.level_y_positions[level]=self.level_y_positions[level-1]-gap
        self._position_nodes(self.tree_structure,x=0,depth=0)
        self.edges.submobjects=[]
        self._create_edges(self.tree_structure)
        if self.backbone_space:self.backbone_anchor.move_to(self._backbone_tail_position())
        for edge,opacity in zip(self.edges,opacities):edge.set_stroke(opacity=opacity)
        self.move_to(center)
        self._arrange_attachments()

    def _arrange_attachments(self):
        if hasattr(self,'leaf_numbers'):
            leaves=sorted((data for data,_ in self.iter_nodes() if not data['children']),
                          key=lambda data:data['mobject'].get_x())
            for label,data in zip(self.leaf_numbers,leaves):label.next_to(data['mobject'],DOWN,buff=.09)

    def motions_to(self,target):return [Transform(self,target)]

    def _extra_parts(self):
        parts={}
        if hasattr(self,'leaf_numbers'):parts['counts']=self.leaf_numbers
        if hasattr(self,'backbone_anchor'):parts['backbone']=self.backbone_anchor
        known={id(self.nodes),id(self.edges),*(id(part) for part in parts.values())}
        parts.update({f'attachment:{index}':part for index,part in enumerate(
            part for part in self.submobjects if id(part) not in known)})
        return parts

    def motions_to(self,target):
        from ..composition import _same_picture
        if len(self.nodes)!=len(target.nodes) or len(self.edges)!=len(target.edges):
            raise ValueError('Changing tree topology requires an explicit tree process')
        motions=[]
        for live,destination in [(self.edges,target.edges),*zip(self.nodes,target.nodes)]:
            if not _same_picture(live,destination):motions.append(Transform(live,destination))
        old,new=self._extra_parts(),target._extra_parts()
        for name,part in old.items():
            if name not in new:motions.append(FadeOut(part))
            elif not _same_picture(part,new[name]):motions.append(Transform(part,new[name]))
        motions.extend(FadeIn(part) for name,part in new.items() if name not in old)
        return motions

    def adopt_layout(self,target):
        # Adopt semantic children separately. Whole-tree become/Transform pads
        # a new leaf-count group with copies of the node group, creating phantom
        # calls and duplicate count labels before the next layout is measured.
        old_extras=self._extra_parts()
        self.edges.become(target.edges.copy())
        for (data,_),(destination,_) in zip(self.iter_nodes(),target.iter_nodes()):
            if hasattr(type(data['mobject']),'adopt_layout'):
                data['mobject'].adopt_layout(destination['mobject'])
                data['label']=data['mobject'].label
                data['shape']=data['circle']=data['mobject'].box
            else:data['mobject'].become(destination['mobject'])
            data['state']=destination['state']
        extras=[]
        for name,part in target._extra_parts().items():
            live=old_extras.get(name)
            if live is None:live=part.copy()
            elif name=='counts':
                labels=[]
                for index,label in enumerate(part):
                    value=live[index] if index<len(live) else label.copy()
                    value.become(label.copy())
                    value.submobjects=[child.copy() for child in label.submobjects]
                    value.tex_string=label.tex_string
                    value.initial_height=label.initial_height
                    value._font_size=label._font_size
                    labels.append(value)
                live.submobjects=labels
            else:live.become(part.copy())
            if name=='counts':self.leaf_numbers=live
            if name=='backbone':self.backbone_anchor=live
            extras.append(live)
        if 'counts' not in target._extra_parts() and hasattr(self,'leaf_numbers'):del self.leaf_numbers
        self.submobjects=[self.edges,self.nodes,*extras]
        self.level_spacing=target.level_spacing
        self.sibling_spacing=target.sibling_spacing
        self.level_y_positions=target.level_y_positions.copy()
        if hasattr(self,'_layered_unroll_nodes'):
            self._layered_unroll_nodes=[(data['mobject'],data['mobject'].copy().set_opacity(1),depth)
                                        for data,depth in self.iter_nodes()]
            self._layered_unroll_edges=[]
            for parent,depth in self.iter_nodes():
                for child,edge in zip(parent['children'],parent['edges']):
                    direction=child['shape'].get_center()-parent['shape'].get_center()
                    full=Line(parent['shape'].get_boundary_point(direction),
                              child['shape'].get_boundary_point(-direction),
                              color=edge.get_stroke_color(),stroke_width=edge.get_stroke_width())
                    self._layered_unroll_edges.append((edge,full,depth+1))
        return self

    def _display_level(self, node_data, recursion_depth):
        if self.level_fn is None:
            return recursion_depth
        level = self.level_fn(node_data["args"])
        if not isinstance(level, int) or level < 0:
            raise ValueError("level_fn must return a nonnegative integer")
        return level

    def _get_subtree_width(self, node_data):
        if not node_data["children"]:
            return max(self.sibling_spacing, node_data["mobject"].width + 0.18)
        children_width = sum(self._get_subtree_width(c) for c in node_data["children"])
        return max(children_width, node_data["mobject"].width + 0.18)

    def _position_nodes(self, node_data, x, depth):
        display_level = self._display_level(node_data, depth)
        y = self.level_y_positions.get(
            display_level, -display_level * self.level_spacing,
        )
        node_data["mobject"].move_to([x, y, 0])

        if not node_data["children"]:
            return

        total_width = sum(self._get_subtree_width(c) for c in node_data["children"])
        current_x = x - total_width / 2.0

        for child in node_data["children"]:
            child_width = self._get_subtree_width(child)
            child_x = current_x + child_width / 2.0
            self._position_nodes(child, child_x, depth + 1)
            current_x += child_width

    def _create_edges(self, node_data):
        for child in node_data["children"]:
            direction = child["shape"].get_center() - node_data["shape"].get_center()
            edge = Line(
                node_data["shape"].get_boundary_point(direction),
                child["shape"].get_boundary_point(-direction),
                color=self.theme.muted,
                stroke_width=2,
            )
            node_data["edges"].append(edge)
            self.edges.add(edge)

            self._create_edges(child)

    def iter_nodes(self):
        """Yield ``(node_data, depth)`` pairs in preorder."""
        def walk(node_data, depth):
            yield node_data, depth
            for child in node_data["children"]:
                yield from walk(child, depth + 1)

        yield from walk(self.tree_structure, 0)

    def _prepare_leaf_counts(self):
        leaves=sorted((data for data,_ in self.iter_nodes() if not data['children']),
                      key=lambda data:data['mobject'].get_x())
        self.leaf_numbers=VGroup(*(LessonStyle(theme=self.theme).math(str(index),
            type_role='label',status='computed').next_to(data['mobject'],DOWN,buff=.09)
            for index,data in enumerate(leaves,1)))
        self.add(self.leaf_numbers)
        return leaves

    def with_state(self,*,leaf_counts):
        target=self.copy()
        if leaf_counts and not hasattr(target,'leaf_numbers'):
            target._prepare_leaf_counts();target.leaf_numbers.set_opacity(0)
        elif not leaf_counts and hasattr(target,'leaf_numbers'):
            target.remove(target.leaf_numbers);del target.leaf_numbers
        return target

    def count_leaves(self):
        """Number leaves beside their calls without replacing the call labels."""
        leaves=sorted((data for data,_ in self.iter_nodes() if not data['children']),
                      key=lambda data:data['mobject'].get_x())
        if not hasattr(self,'leaf_numbers'):self._prepare_leaf_counts()
        self.leaf_numbers.set_opacity(1)
        return AnimationGroup(*(SemanticChange(data['mobject'],status='computed',theme=self.theme)
                                for data in leaves),
                              LaggedStart(*(FadeIn(label) for label in self.leaf_numbers),lag_ratio=.12))

    def annotate(self,node,content,*,side='left'):
        from .teaching import TreeAnnotation
        note=TreeAnnotation(node['mobject'],content,side=side,theme=self.theme)
        self.add(note)
        return FadeIn(note)

    def backbone(self):
        """Keep the first occurrence down the first branch, plus missing states."""
        kept=[];cursor=self.tree_structure
        while True:
            kept.append(cursor)
            if not cursor['children']:break
            cursor=cursor['children'][0]
        keys={self.state_key(node['args']) for node in kept}
        # A leaf sibling can supply a distinct base state (e.g. Fibonacci 1).
        for node,_ in self.iter_nodes():
            if not node['children'] and self.state_key(node['args']) not in keys:
                kept.append(node);keys.add(self.state_key(node['args']))
        return kept

    def fold_to_backbone(self,values):
        """Resolve a state, then fold its duplicate subtrees, from bottom to top."""
        kept=self.backbone();resolved=set()
        def resolve(node):
            key=self.state_key(node['args'])
            resolved.add(key)
            return DeferredAnimation(lambda node=node,key=key:node['mobject'].populate(values[key]),run_time=.34)
        operations=[]
        # A distinct base sibling belongs in the retained state sequence, but
        # a base case does not recursively call that sibling. Place it beyond
        # the spine and retire its old dependency edge instead of inventing one.
        spine=[];cursor=self.tree_structure
        while True:
            spine.append(cursor)
            if not cursor['children']:break
            cursor=cursor['children'][0]
        extra=[node for node in kept if all(node is not member for member in spine)]
        for node in extra:
            old_edge=next(edge for parent,_ in self.iter_nodes()
                for child,edge in zip(parent['children'],parent['edges']) if child is node)
            operations.append(AnimationGroup(Transform(node['mobject'],node['mobject'].copy().move_to(
                self._backbone_tail_position())),FadeOut(old_edge),run_time=.35))
        for node in sorted((n for n in kept if not n['children']),key=lambda n:self.state_key(n['args'])):
            operations.append(resolve(node))
        steps=self.get_backbone_collapse_steps(kept,order='bottom_up')
        for index,step in enumerate(steps):
            canonical=step['canonical']
            if canonical is not None and self.state_key(canonical['args']) not in resolved:
                operations.append(resolve(canonical))
            # Build this fold only when it starts: prior resolutions and folds
            # change the live node labels and positions.
            operations.append(DeferredAnimation(lambda index=index:self.get_backbone_collapse_animations(
                kept,order='bottom_up',merge_run_time=.58,fade_run_time=.04,
                move_edges=False,edge_fade_run_time=.04)[index],run_time=.66))
        for node in sorted(kept,key=lambda n:self.state_key(n['args'])):
            if self.state_key(node['args']) not in resolved:operations.append(resolve(node))
        return Succession(*operations)

    def merge_backbone_into(self,sequence):
        """Survivors travel into the already visible array cells beneath them."""
        kept=sorted(self.backbone(),key=lambda node:self.state_key(node['args']))
        if len(kept)!=len(sequence.row):raise ValueError('One destination cell is required per retained state')
        class MergeIntoCells(AnimationGroup):
            _algovis_component_process=True
            def clean_up_from_scene(group,scene):
                super().clean_up_from_scene(scene)
                # The destination cells already exist. Retire the coincident
                # travelling artwork only after it has arrived, without a
                # second fade across the readable stored answer.
                for node in kept:node['mobject'].set_opacity(0)
        return Succession(FadeOut(self.edges,run_time=.15),
            MergeIntoCells(*(motion for node,cell in zip(kept,sequence.row)
                for motion in (node['mobject'].motions_to(cell)
                    if hasattr(type(node['mobject']),'motions_to') else [Transform(node['mobject'],cell)])),
                lag_ratio=0,run_time=1))

    def get_layers(self):
        """Return node-data lists grouped by depth, from root to leaves."""
        layers = []
        for node_data, depth in self.iter_nodes():
            while len(layers) <= depth:
                layers.append([])
            layers[depth].append(node_data)
        return layers

    def get_duplicate_groups(self, include_singletons=False):
        """Group node data by recursive state, preserving first-seen order."""
        groups = {}
        for node_data, _depth in self.iter_nodes():
            key = self.state_key(node_data["args"])
            groups.setdefault(key, []).append(node_data)
        return {
            key: nodes for key, nodes in groups.items()
            if include_singletons or len(nodes) > 1
        }

    def set_state_colors(self, color_by_key, fill_opacity=0.18,
                         label_color=None):
        """Give every occurrence of the same recursive state the same color.

        ``color_by_key`` may be a mapping keyed by ``state_key(args)`` or a
        callable receiving that key. Missing mapping entries keep their
        existing color. This mutates the tree immediately, which makes it
        useful before a tree reveal as well as before a merge animation.
        """
        for node_data, _depth in self.iter_nodes():
            key = self.state_key(node_data["args"])
            if callable(color_by_key):
                color = color_by_key(key)
            else:
                color = color_by_key.get(key)
            if color is None:
                continue
            node_data["shape"].set_stroke(color).set_fill(
                color, opacity=fill_opacity,
            )
            if label_color is not None:
                node_data["label"].set_color(label_color)
        return self

    def _subtree_parts(self, node_data):
        """Return the visible nodes and edges belonging to one subtree."""
        nodes = VGroup()
        edges = VGroup()

        def walk(current):
            nodes.add(current["mobject"])
            badge = current.get("cache_badge")
            if badge is not None:
                nodes.add(badge)
            for child, edge in zip(current["children"], current["edges"]):
                edges.add(edge)
                walk(child)

        walk(node_data)
        return nodes, edges

    def get_backbone_collapse_steps(self, kept_nodes, order="top_down"):
        """Describe the maximal subtrees that can be removed around a backbone.

        ``kept_nodes`` must contain the root and every ancestor needed to reach
        another kept node. Each returned step is a disjoint subtree, so an
        author can remove repeated work one branch at a time without fading a
        child twice. When the discarded root has the same state as a kept node,
        that node is exposed as ``canonical`` for cache-hit highlighting.
        """
        kept_nodes = list(kept_nodes)
        kept_ids = {id(node) for node in kept_nodes}
        all_nodes = list(self.iter_nodes())
        node_by_id = {id(node): node for node, _depth in all_nodes}
        depth_by_id = {id(node): depth for node, depth in all_nodes}
        parent_by_id = {}
        incoming_edge_by_id = {}
        for parent, _depth in all_nodes:
            for child, edge in zip(parent["children"], parent["edges"]):
                parent_by_id[id(child)] = parent
                incoming_edge_by_id[id(child)] = edge

        unknown = kept_ids.difference(node_by_id)
        if unknown:
            raise ValueError("Every kept node must belong to this RecursiveTree")
        if id(self.tree_structure) not in kept_ids:
            raise ValueError("The root must be included in kept_nodes")
        for node in kept_nodes:
            parent = parent_by_id.get(id(node))
            if parent is not None and id(parent) not in kept_ids:
                raise ValueError(
                    "kept_nodes must form a connected backbone from the root"
                )

        canonical_by_key = {}
        for node, _depth in all_nodes:
            if id(node) in kept_ids:
                canonical_by_key.setdefault(self.state_key(node["args"]), node)

        steps = []

        def visit(current):
            for child in current["children"]:
                if id(child) in kept_ids:
                    visit(child)
                    continue
                nodes, internal_edges = self._subtree_parts(child)
                incoming = incoming_edge_by_id[id(child)]
                steps.append({
                    "root": child,
                    "parent": current,
                    "incoming_edge": incoming,
                    "canonical": canonical_by_key.get(
                        self.state_key(child["args"])
                    ),
                    "nodes": nodes,
                    "edges": VGroup(incoming, *internal_edges),
                    "depth": depth_by_id[id(child)],
                })

        visit(self.tree_structure)
        if order == "bottom_up":
            steps.sort(key=lambda step: step["depth"], reverse=True)
        elif order == "top_down":
            steps.sort(key=lambda step: step["depth"])
        else:
            raise ValueError("order must be 'top_down' or 'bottom_up'")
        return steps

    def get_backbone_collapse_animations(
        self,
        kept_nodes,
        *,
        order="top_down",
        merge_run_time=0.52,
        fade_run_time=0.12,
        move_edges=True,
        edge_fade_run_time=0.08,
    ):
        """Build one merge animation for each discarded subtree.

        Equal-state nodes travel onto their canonical kept nodes, while the
        redundant copy remains visible until it arrives, then dissolves in
        place. By default, branch edges follow their endpoints. Set
        ``move_edges=False`` to dissolve them immediately before the nodes move,
        which is clearer when moving branches would cross retained labels.

        The returned list follows ``order`` and can be interleaved with other
        teaching beats, such as revealing one newly computed value between
        successive folds.
        """
        kept_nodes = list(kept_nodes)
        canonical_by_key = {}
        for node in kept_nodes:
            canonical_by_key.setdefault(self.state_key(node["args"]), node)

        def edge_target(edge, parent_target, child_target):
            target = edge.copy()
            direction = (
                child_target["shape"].get_center()
                - parent_target["shape"].get_center()
            )
            if np.linalg.norm(direction) < 1e-8:
                return None
            target.put_start_and_end_on(
                parent_target["shape"].get_boundary_point(direction),
                child_target["shape"].get_boundary_point(-direction),
            )
            return target

        def fade_in_place(mobjects, run_time):
            """Fade a moved group without interpolating its geometry again."""
            styled_members = None

            def update(_mobject, alpha):
                nonlocal styled_members
                # A preceding cell move adopts clean destination glyphs.
                # Discover them when fading actually starts, not while the
                # future fade is constructed. Cached old glyph references
                # leave the newly adopted values visible without their boxes.
                if styled_members is None:
                    styled_members=[(member,member.get_fill_opacity(),
                        member.get_stroke_opacity(),member.get_background_stroke_opacity())
                        for member in mobjects.family_members_with_points()]
                remaining = 1 - alpha
                for member, fill, stroke, background in styled_members:
                    member.set_fill(opacity=fill * remaining)
                    member.set_stroke(opacity=stroke * remaining)
                    member.set_background_stroke(
                        opacity=background * remaining,
                    )

            return UpdateFromAlphaFunc(
                mobjects, update, run_time=run_time,
            )

        animations = []
        for step in self.get_backbone_collapse_steps(kept_nodes, order=order):
            root_target = step["canonical"]
            destination = (
                root_target["mobject"].get_center()
                if root_target is not None
                else step["root"]["mobject"].get_center()
            )
            merge_animations = []

            def merge_node(current, parent=None, incoming_edge=None):
                current_target = canonical_by_key.get(
                    self.state_key(current["args"])
                )
                if current_target is not None:
                    node_target = current_target["mobject"].copy()
                    live=current['mobject']
                    if hasattr(type(live),'motions_to'):
                        merge_animations.extend(live.motions_to(node_target))
                    else:merge_animations.append(Transform(live,node_target))
                else:
                    merge_animations.append(
                        current["mobject"].animate.move_to(destination)
                        .scale(0.25)
                    )

                badge = current.get("cache_badge")
                if badge is not None:
                    badge_destination = (
                        current_target["mobject"].get_center()
                        if current_target is not None else destination
                    )
                    merge_animations.append(
                        badge.animate.move_to(badge_destination)
                        .scale(0.35)
                    )

                if move_edges and incoming_edge is not None:
                    parent_target = canonical_by_key.get(
                        self.state_key(parent["args"])
                    )
                    target_edge = None
                    if parent_target is not None and current_target is not None:
                        target_edge = edge_target(
                            incoming_edge, parent_target, current_target,
                        )
                    if target_edge is not None:
                        merge_animations.append(Transform(
                            incoming_edge, target_edge,
                        ))
                    else:
                        merge_animations.append(
                            incoming_edge.animate.move_to(destination)
                            .scale(0.25)
                        )

                for child, edge in zip(current["children"], current["edges"]):
                    merge_node(child, current, edge)

            merge_node(step["root"], step["parent"], step["incoming_edge"])
            merge = AnimationGroup(
                *merge_animations, lag_ratio=0,
                run_time=merge_run_time,
            )
            if move_edges:
                animations.append(Succession(
                    merge,
                    fade_in_place(
                        VGroup(step["nodes"], step["edges"]),
                        fade_run_time,
                    ),
                ))
            else:
                animations.append(Succession(
                    fade_in_place(step["edges"], edge_fade_run_time),
                    merge,
                    fade_in_place(step["nodes"], fade_run_time),
                ))
        return animations

    def collapse_to_backbone(
        self,
        kept_nodes,
        *,
        order="top_down",
        merge_run_time=0.52,
        fade_run_time=0.12,
        simultaneous=False,
        move_edges=True,
        edge_fade_run_time=0.08,
    ):
        """Merge discarded work into kept states.

        Set ``simultaneous=True`` to collapse every disjoint branch together;
        otherwise the branches follow ``order``. See
        :meth:`get_backbone_collapse_animations` to interleave individual folds
        with scene-specific explanatory beats.
        """
        animations = self.get_backbone_collapse_animations(
            kept_nodes,
            order=order,
            merge_run_time=merge_run_time,
            fade_run_time=fade_run_time,
            move_edges=move_edges,
            edge_fade_run_time=edge_fade_run_time,
        )
        if not animations:
            return Wait(0)
        if simultaneous:
            return AnimationGroup(*animations, lag_ratio=0)
        return Succession(*animations)

    def highlight_duplicates(self, colors=None, opacity=0.28):
        """Color every repeated state consistently across the recursion tree."""
        # Repeated calls all mean the same thing: wasted work.  A rainbow
        # palette made color identify arbitrary groups instead of meaning.
        palette = colors or [self.theme.danger]
        animations = []
        for index, nodes in enumerate(self.get_duplicate_groups().values()):
            color = palette[index % len(palette)]
            for node in nodes:
                # Transform the complete node. Animating only the circle while
                # its label remains nested in the tree can make Manim detach
                # and reinsert the siblings on different frames.
                target = node["mobject"].copy()
                target[0].set_color(color).set_fill(color, opacity=opacity)
                animations.append(Transform(node["mobject"], target))
        return AnimationGroup(*animations, lag_ratio=0.04)

    def show_cache_hit(self, node_data, color=None):
        """Mark a repeated node as a lookup rather than a recomputation."""
        color = color or self.theme.accent
        badge = Text("cache hit", font_size=16, color=color)
        badge.next_to(node_data["mobject"], RIGHT, buff=0.10)
        node_data["cache_badge"] = badge
        # Keep the badge owned by the tree so clearing or replacing the tree
        # cannot leave an orphaned label in later scenes.
        self.add(badge)
        return AnimationGroup(Indicate(node_data["mobject"], color=color),
                              FadeIn(badge, shift=LEFT * 0.08))

    def build_state_graph(self, direction=DOWN, node_buff=0.28, edge_color=None):
        """Return a DAG containing one node for each unique recursive state."""
        edge_color = edge_color or self.theme.muted
        grouped = self.get_duplicate_groups(include_singletons=True)
        canonical = {key: nodes[0] for key, nodes in grouped.items()}
        depths = {}
        for node_data, depth in self.iter_nodes():
            key = self.state_key(node_data["args"])
            depths[key] = min(depths.get(key, depth), depth)

        graph = VGroup()
        graph.nodes = {}
        graph.edges = VGroup()
        levels = {}
        for key in canonical:
            levels.setdefault(depths[key], []).append(key)
        for depth, keys in sorted(levels.items()):
            row = VGroup()
            for key in keys:
                node = canonical[key]["mobject"].copy()
                graph.nodes[key] = node
                row.add(node)
            row.arrange(RIGHT, buff=node_buff)
            row.move_to(DOWN * depth * 0.9)
            graph.add(row)

        seen_edges = set()
        for node_data, _depth in self.iter_nodes():
            parent_key = self.state_key(node_data["args"])
            for child in node_data["children"]:
                child_key = self.state_key(child["args"])
                pair = (parent_key, child_key)
                if pair in seen_edges:
                    continue
                seen_edges.add(pair)
                parent = graph.nodes[parent_key]
                target = graph.nodes[child_key]
                delta = target.get_center() - parent.get_center()
                edge = Arrow(
                    parent[0].get_boundary_point(delta),
                    target[0].get_boundary_point(-delta),
                    buff=0.02, color=edge_color, stroke_width=2,
                    max_tip_length_to_length_ratio=0.12,
                )
                graph.edges.add(edge)
        graph.add_to_back(graph.edges)
        graph.move_to(self)
        return graph

    def collapse_to_state_graph(self, **kwargs):
        """Replace this tree with its unique-state DAG."""
        self.memoized_graph = self.build_state_graph(**kwargs)
        return ReplacementTransform(self, self.memoized_graph)

    def get_layer_annotations(
        self,
        depths=None,
        label_fn=None,
        side=LEFT,
        buff=0.35,
        guide_buff=0.08,
        guide_color=None,
        guide_opacity=0.5,
        guide_dash_length=0.08,
    ):
        """Build labels and dashed guides aligned to selected tree layers.

        ``label_fn`` receives ``(depth, nodes_at_depth)`` and returns any
        Mobject.  The result is a VGroup with public ``labels`` and ``guides``
        attributes so scenes can animate them together or independently.
        """
        layers = self.get_layers()
        selected = list(range(len(layers))) if depths is None else list(depths)
        labels = VGroup()
        guides = VGroup()
        left_side = side[0] < 0

        for depth in selected:
            if depth < 0 or depth >= len(layers):
                continue
            nodes = layers[depth]
            label = (
                label_fn(depth, nodes)
                if label_fn is not None
                else Text(
                    f"layer {depth}", font_size=18, color=self.theme.muted,
                )
            )
            y = sum(node["mobject"].get_y() for node in nodes) / len(nodes)
            label.next_to(self, LEFT if left_side else RIGHT, buff=buff).set_y(y)
            anchor = min(nodes, key=lambda n: n["mobject"].get_x()) if left_side else max(
                nodes, key=lambda n: n["mobject"].get_x()
            )
            label_point = label.get_right() if left_side else label.get_left()
            node_point = anchor["shape"].get_left() if left_side else anchor["shape"].get_right()
            direction = RIGHT if left_side else LEFT
            guide = DashedLine(
                label_point + direction * guide_buff,
                node_point - direction * guide_buff,
                color=guide_color or self.theme.muted,
                stroke_width=1.2,
                stroke_opacity=guide_opacity,
                dash_length=guide_dash_length,
            )
            labels.add(label)
            guides.add(guide)

        annotations = VGroup(guides, labels)
        annotations.labels = labels
        annotations.guides = guides
        return annotations

    def get_set_state_anim(self, node_data, state):
        """Returns an animation to change a node's state"""
        node_data["state"] = state
        status={NodeState.PENDING:'unseen',NodeState.ACTIVE:'active',NodeState.RESOLVED:'computed'}[state]
        animation=SemanticChange(node_data['mobject'],SemanticProperties('node',status),
            theme=self.theme,part='box',channel='stroke')
        target=animation.target_mobject
        if state == NodeState.ACTIVE:
            target[0].set_color(self.theme.accent).set_stroke(width=4)
        elif state == NodeState.RESOLVED:
            target[0].set_color(self.theme.success).set_fill(
                self.theme.success, opacity=0.3,
            )
        else:
            target[0].set_color(self.theme.node).set_stroke(width=2)
        return animation

    def get_unroll_anim(self, lag_ratio=0.5):
        """Grow edges and reveal nodes in a smooth top-to-bottom wave.

        This is implemented as one animation rather than nested ``FadeIn``
        instances.  Consequently Manim cannot pre-add labels from a future
        branch and briefly expose them before that branch begins.
        """
        node_records = []
        edge_records = []
        max_depth = 0
        for node_data, depth in self.iter_nodes():
            max_depth = max(max_depth, depth)
            node_records.append((node_data["mobject"], node_data["mobject"].copy(), depth))
            for edge in node_data["edges"]:
                # Outgoing edges visually belong to the children they reveal.
                edge_records.append((edge, edge.copy(), depth + 1))

        for node, _original, _depth in node_records:
            node.set_opacity(0)
        for edge, original, _depth in edge_records:
            edge.pointwise_become_partial(original, 0, 0)

        # Values below one stagger levels; each level itself still gets enough
        # time to ease in instead of popping on a single frame.
        level_duration = 1.35
        level_step = max(0.34, min(0.82, float(lag_ratio) * 3.0 + 0.34))
        total = max_depth * level_step + level_duration

        def level_alpha(alpha, depth):
            elapsed = alpha * total - depth * level_step
            return smooth(max(0.0, min(1.0, elapsed / level_duration)))

        def reveal(_tree, alpha):
            for node, original, depth in node_records:
                amount = level_alpha(alpha, depth)
                node.become(
                    original.copy()
                    .scale(0.82 + 0.18 * amount, about_point=original.get_center())
                    .set_opacity(amount)
                )
            for edge, original, depth in edge_records:
                amount = level_alpha(alpha, depth)
                edge.pointwise_become_partial(original, 0, amount)
                edge.set_opacity(amount)

        return UpdateFromAlphaFunc(self, reveal)

    def prepare_layered_unroll(self):
        """Hide a tree once so selected depth ranges can be revealed later.

        This supports narration-driven scenes where the root, its first
        children, and the remaining tree are introduced by separate phrases.
        Pristine copies keep future labels and edges from flashing early.
        """
        if not hasattr(self, "_layered_unroll_nodes"):
            self._layered_unroll_nodes = [
                (node_data["mobject"], node_data["mobject"].copy(), depth)
                for node_data, depth in self.iter_nodes()
            ]
            self._layered_unroll_edges = []
            for node_data, depth in self.iter_nodes():
                for edge in node_data["edges"]:
                    self._layered_unroll_edges.append((edge, edge.copy(), depth + 1))
            for node, _original, _depth in self._layered_unroll_nodes:
                node.set_opacity(0)
            for edge, original, _depth in self._layered_unroll_edges:
                edge.pointwise_become_partial(original, 0, 0)
                edge.set_opacity(0)
        return self

    def get_depth_reveal_anim(self, start_depth, end_depth=None, lag_ratio=0.05):
        """Reveal an inclusive range of prepared tree depths smoothly."""
        self.prepare_layered_unroll()
        end_depth = start_depth if end_depth is None else end_depth
        nodes = [record for record in self._layered_unroll_nodes
                 if start_depth <= record[2] <= end_depth]
        edges = [record for record in self._layered_unroll_edges
                 if start_depth <= record[2] <= end_depth]
        if not nodes and not edges:
            return Wait(0.01)

        span = max(0, end_depth - start_depth)
        level_duration = 1.0
        level_step = max(0.18, min(0.55, float(lag_ratio) * 3.0 + 0.18))
        total = span * level_step + level_duration

        def level_alpha(alpha, depth):
            elapsed = alpha * total - (depth - start_depth) * level_step
            return smooth(max(0.0, min(1.0, elapsed / level_duration)))

        def reveal(_tree, alpha):
            for node, original, depth in nodes:
                amount = level_alpha(alpha, depth)
                node.become(
                    original.copy()
                    .scale(0.84 + 0.16 * amount, about_point=original.get_center())
                    .set_opacity(amount)
                )
            for edge, original, depth in edges:
                amount = level_alpha(alpha, depth)
                edge.pointwise_become_partial(original, 0, amount)
                edge.set_opacity(amount)

        return UpdateFromAlphaFunc(self, reveal)

    def get_node_reveal_anim(self, node_data):
        """Reveal one prepared node together with its incoming edge.

        This is useful when narration names siblings one at a time instead of
        introducing an entire tree layer with one phrase.
        """
        self.prepare_layered_unroll()
        node, original, _depth = next(
            record for record in self._layered_unroll_nodes
            if record[0] is node_data["mobject"]
        )

        incoming_edge = None
        incoming_original = None
        for parent, _parent_depth in self.iter_nodes():
            for child, edge in zip(parent["children"], parent["edges"]):
                if child is not node_data:
                    continue
                incoming_edge, incoming_original, _edge_depth = next(
                    record for record in self._layered_unroll_edges
                    if record[0] is edge
                )
                break
            if incoming_edge is not None:
                break

        def reveal(_tree, alpha):
            amount = smooth(alpha)
            node.become(
                original.copy()
                .scale(0.84 + 0.16 * amount, about_point=original.get_center())
                .set_opacity(amount)
            )
            if incoming_edge is not None:
                incoming_edge.pointwise_become_partial(
                    incoming_original, 0, amount,
                )
                incoming_edge.set_opacity(amount)

        return UpdateFromAlphaFunc(self, reveal)

    def get_fade_in_anim(self):
        """Safely fade in a complete tree without a one-frame label flash.

        Opacity is driven on the actual drawable family members.  Animating
        opacity only on the outer ``VGroup`` lets circles and MathTex glyphs
        initialize at different moments in some renderers.
        """
        members = list(self.family_members_with_points())
        styles = [
            (member, member.get_fill_opacity(), member.get_stroke_opacity())
            for member in members
        ]
        for member, _fill, _stroke in styles:
            member.set_fill(opacity=0)
            member.set_stroke(opacity=0)

        def reveal(_tree, alpha):
            amount = smooth(alpha)
            for member, fill_opacity, stroke_opacity in styles:
                member.set_fill(opacity=fill_opacity * amount)
                member.set_stroke(opacity=stroke_opacity * amount)

        return UpdateFromAlphaFunc(self, reveal)
