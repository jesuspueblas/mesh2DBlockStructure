"""Abstract base class for 2D geometric entities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple

from meshcad.core.geometry.point import Point2D


class GeometryEntity(ABC):
    """Common interface for all 2D geometric entities."""

    @abstractmethod
    def start_point(self) -> Point2D:
        pass

    @abstractmethod
    def end_point(self) -> Point2D:
        pass

    @abstractmethod
    def length(self) -> float:
        pass

    @abstractmethod
    def evaluate(self, t: float) -> Point2D:
        pass

    @abstractmethod
    def sample(self, n: int) -> List[Point2D]:
        pass

    @abstractmethod
    def bounding_box(self) -> Tuple[Point2D, Point2D]:
        pass

    @abstractmethod
    def get_grips(self) -> List[Point2D]:
        """Return internal, non-topological control points.

        The start and end points are managed by topology, not by
        geometry. For an arc, the grip is its center. For a
        spline, the grips are the internal control points.
        """
