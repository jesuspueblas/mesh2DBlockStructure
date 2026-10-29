"""Catmull-Rom interpolating spline through a list of points."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

from meshcad.core.geometry.entity import GeometryEntity
from meshcad.core.geometry.point import Point2D


def _catmull_rom(p0: Point2D, p1: Point2D, p2: Point2D, p3: Point2D,
                 t: float) -> Point2D:
    t2 = t * t
    t3 = t2 * t
    x = 0.5 * (
        2.0 * p1.x
        + (-p0.x + p2.x) * t
        + (2.0 * p0.x - 5.0 * p1.x + 4.0 * p2.x - p3.x) * t2
        + (-p0.x + 3.0 * p1.x - 3.0 * p2.x + p3.x) * t3
    )
    y = 0.5 * (
        2.0 * p1.y
        + (-p0.y + p2.y) * t
        + (2.0 * p0.y - 5.0 * p1.y + 4.0 * p2.y - p3.y) * t2
        + (-p0.y + 3.0 * p1.y - 3.0 * p2.y + p3.y) * t3
    )
    return Point2D(x, y)


@dataclass(frozen=True)
class Spline(GeometryEntity):
    points: Tuple[Point2D, ...]

    def __post_init__(self):
        if len(self.points) < 2:
            raise ValueError("A spline requires at least two points")

    def start_point(self) -> Point2D:
        return self.points[0]

    def end_point(self) -> Point2D:
        return self.points[-1]

    def evaluate(self, t: float) -> Point2D:
        n = len(self.points)
        if n == 2:
            a, b = self.points
            t = max(0.0, min(1.0, t))
            return Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)

        t = max(0.0, min(1.0, t))
        segments = n - 1
        scaled = t * segments
        i = min(int(scaled), segments - 1)
        local_t = scaled - i

        p0 = self.points[i - 1] if i - 1 >= 0 else self.points[0]
        p1 = self.points[i]
        p2 = self.points[i + 1]
        p3 = self.points[i + 2] if i + 2 < n else self.points[-1]

        return _catmull_rom(p0, p1, p2, p3, local_t)

    def sample(self, n: int) -> List[Point2D]:
        if n < 2:
            raise ValueError("n must be >= 2")
        return [self.evaluate(i / (n - 1)) for i in range(n)]

    def length(self) -> float:
        dense = self.sample(200)
        return sum(
            dense[i].distance_to(dense[i + 1]) for i in range(len(dense) - 1)
        )

    def bounding_box(self) -> Tuple[Point2D, Point2D]:
        pts = self.sample(200)
        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        return (Point2D(min(xs), min(ys)), Point2D(max(xs), max(ys)))

    def get_grips(self) -> List[Point2D]:
        return list(self.points[1:-1])
