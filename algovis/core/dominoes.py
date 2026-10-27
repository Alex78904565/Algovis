"""Contact geometry for a row of rigid rectangular dominoes on a floor."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DominoGeometry:
    width: float
    height: float
    gap: float

    def __post_init__(self):
        if not (self.width > 0 and self.height > 0 and 0 < self.gap < self.height):
            raise ValueError("Domino width/height must be positive, with 0 < gap < height")

    @property
    def pitch(self):
        return self.width + self.gap

    @property
    def first_contact(self):
        return math.asin(self.gap / self.height)

    def predecessor_angle(self, next_angle):
        """Angle of the touching domino to the left, without penetrating it.

        Initially its top-right corner touches the next domino's left face.
        Once that face leans past their common resting angle, the next domino's
        bottom-left corner instead supports the predecessor's right face.
        That second contact matters as the last domino reaches the floor.
        """
        if not 0 <= next_angle <= math.pi / 2:
            raise ValueError("Clockwise angles must be between upright and flat")
        reach = self.pitch * math.cos(next_angle) - self.width
        if reach >= 0:
            return next_angle + math.asin(min(1.0, reach / self.height))
        return math.atan2(self.pitch - self.width * math.cos(next_angle),
                          self.width * math.sin(next_angle))

    def angles(self, count, front, front_angle):
        """Earlier dominoes maintain contact; later ones remain upright."""
        if count < 1 or not 0 <= front < count:
            raise ValueError("The falling front must identify a domino in the chain")
        if not 0 <= front_angle <= math.pi / 2:
            raise ValueError("Clockwise angles must be between upright and flat")
        result = [0.0] * count
        result[front] = front_angle
        for index in range(front - 1, -1, -1):
            result[index] = self.predecessor_angle(result[index + 1])
        return result
