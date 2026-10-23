from manim import *
import itertools
import math

from ..theme import DEFAULT_SPACING, DEFAULT_THEME


class StateParameter(VGroup):
    """A labeled discrete parameter whose displayed value can be animated."""

    def __init__(self, name, values, value=None, box_width=0.72,
                 box_height=0.58, color=None, theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        color = color or theme.primary
        self.name = name
        self.values = list(values)
        if not self.values:
            raise ValueError("StateParameter requires at least one value")
        self.value = self.values[0] if value is None else value
        self.box = RoundedRectangle(corner_radius=0.07, width=box_width,
                                    height=box_height, color=color)
        self.value_mobject = MathTex(str(self.value)).scale(0.55).move_to(self.box)
        self.name_label = MathTex(str(name)).scale(0.48).next_to(self.box, UP, buff=0.10)
        self.bound_label = MathTex(
            str(len(self.values)), color=theme.success,
        ).scale(0.42)
        self.bound_label.next_to(self.box, DOWN, buff=DEFAULT_SPACING.tight)
        self.add(self.box, self.value_mobject, self.name_label)

    def set_value(self, value, color=None):
        color = color or self.theme.accent
        if value not in self.values:
            raise ValueError(f"{value!r} is outside this parameter's domain")
        target = MathTex(str(value), color=color).scale(0.55).move_to(self.box)
        old = self.value_mobject
        self.value_mobject = target
        self.value = value
        self.remove(old).add(target)
        return ReplacementTransform(old, target)

    def show_bound(self):
        """Show the number of possible values beneath the parameter."""
        self.add(self.bound_label)
        return FadeIn(self.bound_label, shift=UP * 0.08)


class BinaryStateVector(VGroup):
    """A row of explicit 0/1 state parameters, ideal for introductory TSP."""

    def __init__(self, names, values=None, buff=None,
                 theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        buff = DEFAULT_SPACING.tight if buff is None else buff
        names = list(names)
        values = list(values) if values is not None else [0] * len(names)
        self.parameters = VGroup(*[
            StateParameter(name, [0, 1], value=value, theme=theme)
            for name, value in zip(names, values)
        ]).arrange(RIGHT, buff=buff)
        self.add(self.parameters)

    def flip(self, index, color=None):
        parameter = self.parameters[index]
        return parameter.set_value(1 - parameter.value, color=color)

    def set_bit(self, index, value, color=None):
        return self.parameters[index].set_value(value, color=color)

    def show_bounds(self):
        animations = [parameter.show_bound() for parameter in self.parameters]
        product = MathTex(
            r"2^n\ \text{binary patterns}", color=self.theme.success,
        )
        product.next_to(self, DOWN, buff=0.48)
        self.product_label = product
        self.add(product)
        return Succession(LaggedStart(*animations, lag_ratio=0.12), FadeIn(product))


class StateSpaceVisualizer(VGroup):
    """Display parameter combinations as a countable collection of states."""

    def __init__(self, states, label_fn=None, columns=None, cell_width=1.05,
                 cell_height=0.55, max_visible=48, title=None,
                 theme=DEFAULT_THEME, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        self.states = list(states)
        self.label_fn = label_fn or self._default_label
        visible = self.states[:max_visible]
        self.cards = {}
        cards = VGroup()
        for state in visible:
            box = RoundedRectangle(corner_radius=0.06, width=cell_width,
                                   height=cell_height, stroke_color=theme.muted)
            label = MathTex(self.label_fn(state)).scale(0.42)
            card = VGroup(box, label)
            card.box = box
            self.cards[self._key(state)] = card
            cards.add(card)
        columns = columns or max(1, math.ceil(math.sqrt(len(visible))))
        cards.arrange_in_grid(cols=columns, buff=(0.10, 0.10))
        self.card_group = cards
        self.add(cards)
        if title:
            self.add(Text(
                title, font_size=24, color=theme.primary,
            ).next_to(cards, UP, buff=DEFAULT_SPACING.normal))
        hidden = len(self.states) - len(visible)
        if hidden > 0:
            self.add(Text(f"+ {hidden} more states", font_size=20,
                          color=theme.muted).next_to(
                              cards, DOWN, buff=DEFAULT_SPACING.tight,
                          ))

    @staticmethod
    def _key(state):
        if isinstance(state, list):
            return tuple(state)
        if isinstance(state, set):
            return frozenset(state)
        return state

    @staticmethod
    def _default_label(state):
        if isinstance(state, (tuple, list)):
            return "(" + ",".join(map(str, state)) + ")"
        if isinstance(state, (set, frozenset)):
            return r"\{" + ",".join(map(str, sorted(state))) + r"\}"
        return str(state)

    @classmethod
    def cartesian(cls, *domains, **kwargs):
        return cls(itertools.product(*domains), **kwargs)

    @classmethod
    def intervals(cls, n, **kwargs):
        return cls(((i, j) for i in range(n) for j in range(i, n)), **kwargs)

    @classmethod
    def subsets(cls, items, **kwargs):
        items = list(items)
        states = (frozenset(combo) for size in range(len(items) + 1)
                  for combo in itertools.combinations(items, size))
        return cls(states, **kwargs)

    @classmethod
    def tsp(cls, vertices, representation="binary", **kwargs):
        vertices = list(vertices)
        if representation == "set":
            states = [(current, frozenset(subset))
                      for size in range(len(vertices) + 1)
                      for subset in itertools.combinations(vertices, size)
                      for current in vertices]
            default_label = lambda state: (
                f"({state[0]}," + r"\{" + ",".join(map(str, sorted(state[1]))) + r"\})"
            )
        else:
            states = [(current, *bits) for current in vertices
                      for bits in itertools.product((0, 1), repeat=len(vertices))]
            default_label = lambda state: "(" + ",".join(map(str, state)) + ")"
        label_fn = kwargs.pop("label_fn", default_label)
        return cls(states, label_fn=label_fn, **kwargs)

    def highlight_state(self, state, color=None):
        color = color or self.theme.accent
        card = self.cards[self._key(state)]
        return card.box.animate.set_color(color).set_fill(color, opacity=0.25).set_stroke(width=3)

    def count_label(self, expression=None, color=None):
        color = color or self.theme.success
        return MathTex(expression or str(len(self.states)), color=color).next_to(self, DOWN, buff=0.25)
