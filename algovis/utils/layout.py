from manim import *

class PanelLayout:
    """
    Helper to manage scene real estate by defining logical regions.
    """
    def __init__(self):
        self.top = UP * 3
        self.bottom = DOWN * 3
        self.left = LEFT * 4
        self.right = RIGHT * 4
        self.center = ORIGIN

    def get_left_panel(self):
        return LEFT * 3.5

    def get_right_panel(self):
        return RIGHT * 3.5

class SmartBulletedList(VGroup):
    """
    An improved BulletedList with better alignment and dot scaling.
    """
    def __init__(self, *items, buff=0.5, dot_scale_factor=1, **kwargs):
        super().__init__(**kwargs)
        self.items = VGroup()
        for item in items:
            line = Tex(r"{{$\bullet$ }}" + item)
            line[0].scale(dot_scale_factor)
            line[0].next_to(line[1], LEFT)
            self.items.add(line)
        self.items.arrange(DOWN, aligned_edge=LEFT, buff=buff)
        self.add(self.items)
