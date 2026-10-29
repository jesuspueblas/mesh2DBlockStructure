"""Point in the 2D plane."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Point2D:
    """Immutable point in the 2D plane."""

    x: float
    y: float

    def __sub__(self, other: "Point2D") -> "object":
        from meshcad.core.geometry.vector import Vector2D

        return Vector2D(self.x - other.x, self.y - other.y)

    def __add__(self, other) -> "Point2D":
        return Point2D(self.x + other.x, self.y + other.y)

    def distance_to(self, other: "Point2D") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def __repr__(self) -> str:
        return "Point2D({:g}, {:g})".format(self.x, self.y)
