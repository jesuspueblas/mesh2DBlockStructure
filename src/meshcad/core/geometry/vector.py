"""Vector in the 2D plane."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vector2D:
    """Immutable vector in the 2D plane."""

    x: float
    y: float

    def __add__(self, other: "Vector2D") -> "Vector2D":
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2D") -> "Vector2D":
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2D":
        return Vector2D(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vector2D":
        return self * scalar

    def __neg__(self) -> "Vector2D":
        return Vector2D(-self.x, -self.y)

    def norm(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> "Vector2D":
        n = self.norm()
        if n == 0:
            raise ValueError("The zero vector cannot be normalized")
        return Vector2D(self.x / n, self.y / n)

    def dot(self, other: "Vector2D") -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: "Vector2D") -> float:
        return self.x * other.y - self.y * other.x

    def angle(self) -> float:
        return math.atan2(self.y, self.x)

    def rotate(self, angle: float) -> "Vector2D":
        c, s = math.cos(angle), math.sin(angle)
        return Vector2D(self.x * c - self.y * s, self.x * s + self.y * c)
