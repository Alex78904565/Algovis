from manim import *
import re

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
                 preserve_destination_layout=False, copy_only=None, **kwargs):
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
        # Carry only the actual glyphs. A backing rectangle looked like a
        # chunk of the slide being picked up and could obscure other rows.
        # Keep a visible copy throughout arrival and local substitution;
        # fading it out before revealing the result caused a blank frame.
        # Editable rows intentionally keep their named terms and baseline
        # anchors. Their hierarchy need not resemble the reference's VGroup
        # hierarchy, even when both paint the identical formula. Match the
        # actual TeX glyphs for the transient copy instead of making Manim
        # pad term containers/anchors into duplicate letters on arrival.
        def ink(mobject):
            glyphs = []
            for part in mobject.family_members_with_points():
                # align_data can leave padding points on a term/container,
                # or invisible point-bearing placeholders below it. Neither
                # is a painted TeX glyph. Inspect each leaf's own ink, not a
                # container's bounding box (which includes its children).
                if (not isinstance(part, VMobject) or isinstance(part, VectorizedPoint)
                        or part.submobjects):
                    continue
                extent = np.ptp(part.points[:, :2], axis=0)
                filled = float(np.max(part.get_fill_opacity())) > 0 and bool(np.all(extent > 1e-10))
                stroked = (float(np.max(part.get_stroke_opacity())) > 0
                           and float(np.max(part.get_stroke_width())) > 0
                           and bool(np.any(extent > 1e-10)))
                if filled or stroked:
                    glyphs.append(part)
            return glyphs

        source_ink, target_ink = ink(definition), ink(result)
        equivalent_structured = bool(
            source_text and source_text == target_text
        )
        if equivalent_structured and len(source_ink) != len(target_ink):
            raise ValueError(f'Equivalent structured copies require matching visible glyphs '
                             f'({len(source_ink)} source, {len(target_ink)} destination); '
                             'select the formula without extra artwork or repair its glyph ownership')
        self._glyph_aligned_copy = equivalent_structured
        self._continuous_copy = (bool(copy_only) if copy_only is not None else
            bool(equivalent_structured or (not source_text and not target_text
                                          and type(definition) is type(result))))
        self._algovis_copy_contract = {
            'equivalentFormula': bool(source_text and source_text == target_text),
            'structuredDestination': bool(getattr(result, '_algovis_preserve_structure', False)),
            'strategy': 'glyphs' if self._glyph_aligned_copy else 'native',
            'sourceGlyphs': len(source_ink), 'destinationGlyphs': len(target_ink),
            'formattingDuringTravel': self._continuous_copy,
            'pathArc':float(path_arc),'waypoints':len(via),
        }
        # A previous parentheses-to-brackets transform can subdivide a
        # glyph's curves. The visible glyph still corresponds to the same
        # destination glyph; Transform aligns those curve points locally.
        # Requiring equal point counts would silently restore the unsafe
        # container-level morph for already edited formulas.

        def copy_formula(mobject):
            if not self._glyph_aligned_copy:
                return mobject.copy()
            copied = VGroup(*[part.copy() for part in ink(mobject)])
            copied._algovis_label = formula_text(mobject)
            return copied

        self._copy_formula = copy_formula
        self.travelling_formula = copy_formula(definition)
        self.traveller = self.travelling_formula.set_z_index(30)
        self._arrival_target = copy_formula(result) if self._glyph_aligned_copy else result
        landing = self._arrival_target if self._continuous_copy else self.traveller.copy().move_to(result)
        self.landing = landing
        self.waypoints = [self.traveller.copy().move_to(point) for point in via]
        self.waypoint_positions = [point.copy() for point in via]
        # Route around a dense proof instead of carrying the copy through its
        # intervening rows. Each leg preserves the complete formula geometry.
        stops = [*self.waypoints, landing]
        travel_duration=1. if self._continuous_copy else .70
        travel = [Transform(self.traveller, stop,
                            path_arc=0 if self.waypoints else path_arc,
                            run_time=travel_duration / len(stops)) for stop in stops]
        arrival = [Succession(*travel, run_time=travel_duration)]
        if application is not None:
            # Clear the old subexpression as the readable copy approaches,
            # rather than superimposing both formulas through most of arrival.
            fade_start=.30*travel_duration
            arrival.append(Succession(Wait(fade_start),FadeOut(application,run_time=.25*travel_duration)))
        transfer = AnimationGroup(*arrival,lag_ratio=0,run_time=1.) if self._continuous_copy else Succession(
            AnimationGroup(*arrival, lag_ratio=0, run_time=0.70),
            Transform(self.traveller, self._arrival_target, run_time=0.30),
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
        self.traveller.become(self._copy_formula(self.definition)).set_z_index(30)
        if self._glyph_aligned_copy:
            self._arrival_target.become(self._copy_formula(self.result))
        if not self._continuous_copy:
            self.landing.become(self.traveller.copy().move_to(self.result))
        for index,(waypoint, position) in enumerate(zip(self.waypoints, self.waypoint_positions)):
            waypoint.become(self.traveller.copy())
            if self._continuous_copy:
                source=self.traveller.copy();target=self._arrival_target.copy()
                source.align_data(target)
                waypoint.align_data(target)
                waypoint.interpolate(source,target,(index+1)/(len(self.waypoints)+1))
            waypoint.move_to(position)
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
