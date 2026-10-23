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
