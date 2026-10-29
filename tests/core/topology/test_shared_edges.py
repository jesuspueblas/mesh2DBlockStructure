"""Verify that two loops can share the same edge.

This is a fundamental property of the mesher: if two blocks share an edge,
that edge is represented by a single Edge object and therefore has a single
node distribution.
"""

from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.topology.loop import Loop
from meshcad.core.topology.topology import Topology


def build_two_squares():
    """Build two squares that share the central vertical edge.

    Topology (vertices):
        v2(0,1) --- v3(1,1) --- v4(2,1)
        |           |           |
        v0(0,0) --- v1(1,0) --- v5(2,0)

    Left square:  v0 -> v1 -> v3 -> v2 -> v0
    Right square: v1 -> v5 -> v4 -> v3 -> v1
    Shared edge:  v1 -> v3
    """
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    v2 = t.add_vertex(Point2D(0, 1))
    v3 = t.add_vertex(Point2D(1, 1))
    v4 = t.add_vertex(Point2D(2, 1))
    v5 = t.add_vertex(Point2D(2, 0))

    e_bottom_left = t.add_edge(v0, v1, Line(v0.point, v1.point))
    e_left = t.add_edge(v0, v2, Line(v0.point, v2.point))
    e_top_left = t.add_edge(v2, v3, Line(v2.point, v3.point))
    e_shared = t.add_edge(v1, v3, Line(v1.point, v3.point))
    e_bottom_right = t.add_edge(v1, v5, Line(v1.point, v5.point))
    e_right = t.add_edge(v5, v4, Line(v5.point, v4.point))
    e_top_right = t.add_edge(v3, v4, Line(v3.point, v4.point))

    left = Loop()
    left.add_edge(e_bottom_left.id)
    left.add_edge(e_shared.id)
    left.add_edge(e_top_left.id, reversed=True)  # v3 -> v2
    left.add_edge(e_left.id, reversed=True)      # v2 -> v0

    right = Loop()
    right.add_edge(e_shared.id, reversed=True)   # v1 -> v3 reversed: v3 -> v1
    # The intended path is v1 -> v5 -> v4 -> v3 -> v1.
    # e_shared runs from v1 to v3, so it must be reversed to go from v3 to v1.
    # Rebuild the right loop starting at v1:
    right = Loop()
    right.add_edge(e_bottom_right.id)            # v1 -> v5
    right.add_edge(e_right.id)                   # v5 -> v4
    right.add_edge(e_top_right.id, reversed=True)  # v4 -> v3
    right.add_edge(e_shared.id, reversed=True)   # v3 -> v1

    return t, left, right, e_shared


def test_left_square_is_closed():
    t, left, right, _ = build_two_squares()
    assert left.is_closed(t)
    left.validate(t)


def test_right_square_is_closed():
    t, left, right, _ = build_two_squares()
    assert right.is_closed(t)
    right.validate(t)


def test_shared_edge_is_the_same_object():
    t, left, right, e_shared = build_two_squares()
    # The shared edge appears in both loops with the same ID.
    left_ids = [oe.edge_id for oe in left]
    right_ids = [oe.edge_id for oe in right]
    assert e_shared.id in left_ids
    assert e_shared.id in right_ids
    # It is literally the same object in the topology.
    assert t.get_edge(e_shared.id) is e_shared


def test_shared_edge_appears_once_in_topology():
    t, _, _, e_shared = build_two_squares()
    occurrences = sum(1 for e in t.edges() if e.id == e_shared.id)
    assert occurrences == 1
