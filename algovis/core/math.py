from manim import *
import re
from collections import defaultdict, deque

class Function(VGroup):
    """
    A Mobject representing a mathematical function f(x) = ...
    Supports automatic parameter identification and highlighting.
    """
    def __init__(self, name, parameter, value, *args, **kwargs):
        super().__init__()
        self.name = name
        self.parameter = parameter
        self.value = value
        self.args = args
        self.kwargs = kwargs

        # Split the RHS value by parameter instances
        # e.g. "f(n-1) + f(n-2)" split by "n" -> ["f(", "-1) + f(", "-2)"]
        parts = re.split(f"({re.escape(parameter)})", value)

        # Build list of string pieces for MathTex
        # Piece 0: "f("
        # Piece 1: "n"
        # Piece 2: ")="
        # Subsequent pieces alternate: [other_text, param, other_text, param, ...]
        tex_args = [f"{name}(", parameter, ")="] + parts

        # Passing separate string arguments forces MathTex to create separate submobjects reliably
        self.tex = MathTex(*tex_args, *args, **kwargs)

        # Index 1 is the main param on LHS
        # In tex_args[3:], odd indices corresponding to parameter matches in re.split
        self.paraminstances = [self.tex[1]] + [
            self.tex[3 + i] for i, part in enumerate(parts) if part == parameter
        ]

        self.funcpieces = [self.tex[0], self.tex[2]]
        self.add(self.tex)

    def get_application(self, param_str):
        """Returns a new Function object representing the application f(param_str)"""
        new_value = self.value.replace(self.parameter, param_str)
        return Function(self.name, param_str, new_value, *self.args, **self.kwargs).move_to(self.get_center()).align_to(self, LEFT)

    def get_tex_string(self):
        """Returns the raw TeX string for the function"""
        return f"{self.name}({self.parameter})={self.value}"

class ApplyFunction(Succession):
    """
    Animation that highlights a parameter and substitutes it into the function.
    """
    def __init__(self, funcobj, paramobj, *args, **kwargs):
        # 1. Create boxes around parameter instances in the function
        boxes = VGroup(*[SurroundingRectangle(p, color=YELLOW) for p in funcobj.paraminstances])

        # 2. Create box around the argument being passed
        arg_box = SurroundingRectangle(paramobj, color=YELLOW)

        # 3. Create the target function.  Transform the original object in place
        # so callers can continue to animate (or remove) ``funcobj`` afterwards.
        new_func = funcobj.get_application(paramobj.get_tex_string())
        new_boxes = VGroup(*[SurroundingRectangle(p, color=YELLOW) for p in new_func.paraminstances])

        # 4. Animation sequence
        super().__init__(
            Create(arg_box),
            Create(boxes),
            AnimationGroup(
                Transform(funcobj, new_func),
                Transform(boxes, new_boxes),
                FadeOut(paramobj, shift=UP * 0.2)
            ),
            AnimationGroup(
                Uncreate(arg_box),
                Uncreate(boxes)
            ),
            *args, **kwargs
        )

class Substitute(Succession):
    """
    Animates the substitution of a sub-expression with its value.
    Example: f(3) -> 2
    """
    def __init__(self, source_mobject, target_mobject, *args, **kwargs):
        box = SurroundingRectangle(source_mobject, color=BLUE)
        super().__init__(
            Create(box),
            ReplacementTransform(source_mobject, target_mobject),
            Uncreate(box),
            *args, **kwargs
        )


class ApplyDefinition(AnimationGroup):
    """Carry a copy of a visible definition to its application.

    The definition stays visible. Only ``application`` is replaced by the
    pre-positioned ``result``; surrounding equation terms remain untouched.
    Use selectable subexpressions, e.g.::

        self.play(ApplyDefinition(hypothesis_rhs, child_call, expanded_sum))

    The definition and application must already be visible in the scene.
    Pass ``None`` for application when filling a previously blank position.
    Optional ``via`` points route the rigid copy around intervening content.
    ``preserve_destination_layout`` keeps an explicitly arranged result, useful
    when selected terms have gaps because intermediate terms were omitted.
    """

    def __init__(self, definition, application, result, *, path_arc=-PI / 8, via=(),
                 definition_label=None, result_label=None,
                 preserve_destination_layout=False, **kwargs):
        if definition is application:
            raise ValueError("The definition and its application must be distinct")
        if result is definition or result is application:
            raise ValueError("The result must be a new, pre-positioned mobject")
        self.definition = definition
        self.application = application
        self.result = result
        self._adopted = False
        if definition_label:
            definition._algovis_label = str(definition_label)
        if result_label:
            result._algovis_label = str(result_label)
        def formula_text(mobject):
            if hasattr(mobject, 'tex_string'):
                return mobject.tex_string
            return ''.join(formula_text(child) for child in mobject.submobjects)

        source_text = ''.join(formula_text(definition).split())
        target_text = ''.join(formula_text(result).split())
        if source_text and source_text == target_text and not preserve_destination_layout:
            # Inspection contracts belong to the destination's role, even
            # when its glyphs come from a differently sized reference row.
            contracts = defaultdict(deque)
            for part in result.get_family():
                text = getattr(part, 'tex_string', None)
                if isinstance(text, str):
                    # Include unregistered occurrences too. A condition's w
                    # need not share the role of an argument's earlier w.
                    contracts[text].append((
                        getattr(part, '_algovis_typography_group', None),
                        getattr(part, '_algovis_type_role', 'equation')))
            # An identical formula must travel as a rigid copy. Manim's
            # hierarchy matching can otherwise pair the zero in f(0) with
            # the zero after '=' when a VGroup lands in a MathTex object.
            destination = definition.copy()
            destination.scale_to_fit_height(result.height).move_to(result)
            # Canonicalizing the geometry must not discard a caller's uniform
            # semantic destination color (e.g. green for a proved conclusion).
            result_colors = {part.get_color().to_hex()
                             for part in result.family_members_with_points()}
            if len(result_colors) == 1:
                destination.set_color(next(iter(result_colors)))
            # become() aligns mismatched families, padding a single MathTex
            # part into several copies when the source is a selected term.
            # Preserve the rigid copy's actual hierarchy as well as its paint.
            result.become(destination)
            result.submobjects = [child.copy() for child in destination.submobjects]
            for part in result.get_family():
                # The rigid copy's calibrated font reference still measures
                # its scaled geometry. A selected MathTexPart may have no
                # native font_size, so keep that reference while retagging.
                for attribute in ('_algovis_typography_group', '_algovis_type_role'):
                    if hasattr(part, attribute):
                        delattr(part, attribute)
            from ..layout import LessonStyle
            for part in result.get_family():
                matching = contracts.get(getattr(part, 'tex_string', None))
                if not matching:
                    continue
                peers, role = matching.popleft()
                if peers:
                    LessonStyle._watch_type(part, peers, role)
                else:
                    # A parent may just have registered its whole formula;
                    # preserve a destination child's explicit exception.
                    for attribute in ('_algovis_typography_group', '_algovis_type_role'):
                        if hasattr(part, attribute):
                            delattr(part, attribute)
        # Carry only the actual glyphs. A backing rectangle looked like a
        # chunk of the slide being picked up and could obscure other rows.
        # Keep a visible copy throughout arrival and local substitution;
        # fading it out before revealing the result caused a blank frame.
        self.travelling_formula = definition.copy()
        self.traveller = self.travelling_formula.set_z_index(30)
        landing = self.traveller.copy().move_to(result)
        self.landing = landing
        self.waypoints = [self.traveller.copy().move_to(point) for point in via]
        self.waypoint_positions = [point.copy() for point in via]
        # Route around a dense proof instead of carrying the copy through its
        # intervening rows. Each leg preserves the complete formula geometry.
        stops = [*self.waypoints, landing]
        travel = [Transform(self.traveller, stop,
                            path_arc=0 if self.waypoints else path_arc,
                            run_time=0.70 / len(stops)) for stop in stops]
        arrival = [Succession(*travel, run_time=0.70)]
        if application is not None:
            arrival.append(Succession(Wait(0.55), FadeOut(application, run_time=0.15)))
        transfer = Succession(
            AnimationGroup(*arrival, lag_ratio=0, run_time=0.70),
            Transform(self.traveller, result, run_time=0.30),
        )
        super().__init__(
            transfer,
            lag_ratio=0,
            introducer=True,
            **kwargs,
        )

    def begin(self):
        # In a Succession the source may move or resize before this transfer
        # starts. Copy its visible geometry now, rather than reviving the
        # position it had when the animation sequence was constructed.
        self._adopted = False
        self.traveller.become(self.definition.copy()).set_z_index(30)
        self.landing.become(self.traveller.copy().move_to(self.result))
        for waypoint, position in zip(self.waypoints, self.waypoint_positions):
            waypoint.become(self.traveller.copy().move_to(position))
        super().begin()

    def _setup_scene(self, scene):
        # A pre-laid-out equation may already own the hidden destination.
        # Detach it before the first frame, so it is not visible underneath
        # the travelling copy. Remove descendants too: Manim can dissolve
        # an animated container into separate scene objects.
        scene.remove(*self.result.get_family())
        # A delayed application must not be auto-added by an enclosing
        # Succession before its turn. Introduce the copy only on activation.
        scene.add(self.traveller)
        super()._setup_scene(scene)

    def clean_up_from_scene(self, scene):
        # Succession can clean a child when advancing and again when the
        # enclosing sequence finishes. Re-adopting here could resurrect a
        # formula that a later substitution already replaced.
        if self._adopted:
            return
        super().clean_up_from_scene(scene)
        # The copy already paints the exact final result on the last frame.
        # Adopt the caller's result without a fade, gap, or geometry change.
        scene.remove(*self.traveller.get_family())
        if self.application is not None:
            scene.remove(*self.application.get_family())
        scene.add(self.result)
        self._adopted = True
