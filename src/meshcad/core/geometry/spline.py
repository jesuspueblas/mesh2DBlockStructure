"""Catmull-Rom interpolating spline through a list of points."""

from __future__ import annotations

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


@dataclass(frozen=True)
class SplineSegment(GeometryEntity):
    """A parameter-range view of a spline, preserving its exact shape."""

    spline: Spline
    start_t: float
    end_t: float
    start_offset: Point2D = Point2D(0.0, 0.0)
    end_offset: Point2D = Point2D(0.0, 0.0)

    def __post_init__(self):
        if not 0.0 <= self.start_t < self.end_t <= 1.0:
            raise ValueError("Spline segment parameters must satisfy 0 <= start < end <= 1")

    def start_point(self) -> Point2D:
        return self.evaluate(0.0)

    def end_point(self) -> Point2D:
        return self.evaluate(1.0)

    def length(self) -> float:
        points = self.sample(200)
        return sum(
            points[i].distance_to(points[i + 1])
            for i in range(len(points) - 1)
        )

    def evaluate(self, t: float) -> Point2D:
        t = max(0.0, min(1.0, t))
        point = self.spline.evaluate(
            self.start_t + (self.end_t - self.start_t) * t
        )
        return Point2D(
            point.x + self.start_offset.x * (1.0 - t) + self.end_offset.x * t,
            point.y + self.start_offset.y * (1.0 - t) + self.end_offset.y * t,
        )

    def sample(self, n: int) -> List[Point2D]:
        if n < 2:
            raise ValueError("n must be >= 2")
        return [self.evaluate(i / (n - 1)) for i in range(n)]

    def bounding_box(self) -> Tuple[Point2D, Point2D]:
        points = self.sample(200)
        xs = [point.x for point in points]
        ys = [point.y for point in points]
        return Point2D(min(xs), min(ys)), Point2D(max(xs), max(ys))

    def get_grips(self) -> List[Point2D]:
        point_count = len(self.spline.points)
        return [
            self.spline.points[index]
            for index in range(1, point_count - 1)
            if self.start_t < index / (point_count - 1) < self.end_t
        ]

    def with_endpoints(self, start: Point2D, end: Point2D) -> SplineSegment:
        current_start = self.start_point()
        current_end = self.end_point()
        return SplineSegment(
            self.spline,
            self.start_t,
            self.end_t,
            Point2D(
                self.start_offset.x + start.x - current_start.x,
                self.start_offset.y + start.y - current_start.y,
            ),
            Point2D(
                self.end_offset.x + end.x - current_end.x,
                self.end_offset.y + end.y - current_end.y,
            ),
        )

    def with_grip(self, grip_index: int, point: Point2D) -> SplineSegment:
        point_count = len(self.spline.points)
        indices = [
            index
            for index in range(1, point_count - 1)
            if self.start_t < index / (point_count - 1) < self.end_t
        ]
        control_index = indices[grip_index]
        points = list(self.spline.points)
        points[control_index] = point
        updated = SplineSegment(
            Spline(tuple(points)),
            self.start_t,
            self.end_t,
            self.start_offset,
            self.end_offset,
        )
        return updated.with_endpoints(self.start_point(), self.end_point())
