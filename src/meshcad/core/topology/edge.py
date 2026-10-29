"""Topological edge and its oriented use within a loop."""

from __future__ import annotations

from dataclasses import dataclass

from meshcad.core.geometry.entity import GeometryEntity


@dataclass(frozen=True)
class Edge:
    """Topological edge between two vertices.

    The underlying geometry (Line, Arc, Spline) defines the edge shape and
    always runs from start_vertex to end_vertex. If a loop traverses it in
    the opposite direction, the edge is not duplicated; an OrientedEdge
    with reversed=True is used instead.
    """

    id: int
    start_vertex_id: int
    end_vertex_id: int
    geometry: GeometryEntity

    def __repr__(self) -> str:
        return "Edge(id={}, v{} -> v{})".format(
            self.id, self.start_vertex_id, self.end_vertex_id
        )


@dataclass(frozen=True)
class OrientedEdge:
    """A specific use of an edge within a loop.

    reversed=False: the loop traverses the edge in its natural direction
                    (start_vertex -> end_vertex).
    reversed=True:  the loop traverses the edge in reverse.
    """

    edge_id: int
    reversed: bool = False
