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
    """

    def __init__(self, definition, application, result, *, path_arc=-PI / 8,
                 definition_label=None, result_label=None, **kwargs):
        if definition is application:
            raise ValueError("The definition and its application must be distinct")
        if result is definition or result is application:
            raise ValueError("The result must be a new, pre-positioned mobject")
        self.definition = definition
        self.application = application
        self.result = result
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
        if source_text and source_text == target_text:
            # An identical formula must travel as a rigid copy. Manim's
            # hierarchy matching can otherwise pair the zero in f(0) with
            # the zero after '=' when a VGroup lands in a MathTex object.
            destination = definition.copy()
            destination.stretch_to_fit_width(result.width)
            destination.stretch_to_fit_height(result.height).move_to(result)
            result.become(destination)
        # Carry readable glyphs, rather than morphing an entire definition
        # into different symbols while it flies across other proof rows.
        # An opaque backing keeps both copies legible during the transfer.
        self.travelling_formula = definition.copy()
        backing = BackgroundRectangle(
            self.travelling_formula, buff=0.055,
            fill_color=config.background_color, fill_opacity=1, stroke_width=0,
        )
        self.traveller = VGroup(backing, self.travelling_formula).set_z_index(30)
        landing = self.traveller.copy().move_to(result)
        self.landing = landing
        cleanup = [FadeOut(self.traveller)]
        if application is not None:
            cleanup.append(FadeOut(application))
        transfer = Succession(
            Transform(self.traveller, landing, path_arc=path_arc, run_time=0.68),
            AnimationGroup(*cleanup, run_time=0.12),
            FadeIn(result, run_time=0.20),
        )
        super().__init__(
            transfer,
            lag_ratio=0,
            **kwargs,
        )

    def _setup_scene(self, scene):
        # Theme backgrounds can differ from Manim's global configuration.
        # Both ends of the move must match the actual camera background.
        for chip in (self.traveller, self.landing):
            chip[0].set_fill(scene.camera.background_color, opacity=1)
        # A pre-laid-out equation may already own the hidden destination.
        # Detach it before the first frame, so it is not visible underneath
        # the travelling copy. Remove descendants too: Manim can dissolve
        # an animated container into separate scene objects.
        scene.remove(*self.result.get_family())
        super()._setup_scene(scene)
