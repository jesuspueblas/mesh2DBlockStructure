"""Circular arc traversed counterclockwise."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

from meshcad.core.geometry.entity import GeometryEntity
from meshcad.core.geometry.point import Point2D

TWO_PI = 2.0 * math.pi


@dataclass(frozen=True)
class Arc(GeometryEntity):
    center: Point2D
    radius: float
    start_angle: float
    end_angle: float

    def __post_init__(self):
        if self.radius <= 0:
            raise ValueError("The radius must be positive")

    def angle_span(self) -> float:
        span = self.end_angle - self.start_angle
        while span <= 0:
            span += TWO_PI
        return span

    def point_at_angle(self, angle: float) -> Point2D:
        return Point2D(
            self.center.x + self.radius * math.cos(angle),
            self.center.y + self.radius * math.sin(angle),
        )

    def start_point(self) -> Point2D:
        return self.point_at_angle(self.start_angle)

    def end_point(self) -> Point2D:
        return self.point_at_angle(self.end_angle)

    def length(self) -> float:
        return self.radius * self.angle_span()

    def evaluate(self, t: float) -> Point2D:
        t = max(0.0, min(1.0, t))
        return self.point_at_angle(self.start_angle + self.angle_span() * t)

    def sample(self, n: int) -> List[Point2D]:
        if n < 2:
            raise ValueError("n must be >= 2")
        return [self.evaluate(i / (n - 1)) for i in range(n)]

    def bounding_box(self) -> Tuple[Point2D, Point2D]:
        pts = [self.start_point(), self.end_point()]
        for k in range(4):
            a = k * math.pi / 2
            if self._angle_in_span(a):
                pts.append(self.point_at_angle(a))
        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        return (Point2D(min(xs), min(ys)), Point2D(max(xs), max(ys)))

    def _angle_in_span(self, angle: float) -> bool:
        delta = (angle - self.start_angle) % TWO_PI
        return delta <= self.angle_span() + 1e-9

    def get_grips(self) -> List[Point2D]:
        return [self.center]
