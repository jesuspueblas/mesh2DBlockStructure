"""Topological vertex: point with a stable identifier."""

from __future__ import annotations

from dataclasses import dataclass

from meshcad.core.geometry.point import Point2D


@dataclass(frozen=True)
class Vertex:
    """Topological vertex.

    The ID is assigned by the Topology container. The point is the vertex's
    geometric representation.
    """

    id: int
    point: Point2D

    def __repr__(self) -> str:
        return "Vertex(id={}, point={!r})".format(self.id, self.point)
