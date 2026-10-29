import math

import pytest

from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.topology.loop import Loop
from meshcad.core.topology.topology import Topology


def make_triangle():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    v2 = t.add_vertex(Point2D(0, 1))
    e0 = t.add_edge(v0, v1, Line(v0.point, v1.point))
    e1 = t.add_edge(v1, v2, Line(v1.point, v2.point))
    e2 = t.add_edge(v2, v0, Line(v2.point, v0.point))
    return t, (v0, v1, v2), (e0, e1, e2)


def test_empty_loop():
    loop = Loop()
    assert len(loop) == 0
    t = Topology()
    assert not loop.is_closed(t)


def test_triangle_closed():
    t, (v0, v1, v2), (e0, e1, e2) = make_triangle()
    loop = Loop()
    loop.add_edge(e0.id)
    loop.add_edge(e1.id)
    loop.add_edge(e2.id)
    assert loop.is_closed(t)
    loop.validate(t)


def test_triangle_ordered_vertices():
    t, (v0, v1, v2), (e0, e1, e2) = make_triangle()
    loop = Loop()
    loop.add_edge(e0.id)
    loop.add_edge(e1.id)
    loop.add_edge(e2.id)
    assert loop.ordered_vertex_ids(t) == [v0.id, v1.id, v2.id, v0.id]


def test_open_chain_not_closed():
    t, (v0, v1, v2), (e0, e1, e2) = make_triangle()
    loop = Loop()
    loop.add_edge(e0.id)
    loop.add_edge(e1.id)
    assert not loop.is_closed(t)


def test_missing_edge_not_closed():
    t, _, (e0, _, _) = make_triangle()
    loop = Loop()
    loop.add_edge(e0.id)
    loop.add_edge(999)
    assert not loop.is_closed(t)


def test_validate_raises_for_open():
    t, _, (e0, e1, _) = make_triangle()
    loop = Loop()
    loop.add_edge(e0.id)
    loop.add_edge(e1.id)
    with pytest.raises(ValueError):
        loop.validate(t)


def test_triangle_all_reversed_is_closed():
    t, (v0, v1, v2), (e0, e1, e2) = make_triangle()
    loop = Loop()
    loop.add_edge(e2.id, reversed=True)
    loop.add_edge(e1.id, reversed=True)
    loop.add_edge(e0.id, reversed=True)
    assert loop.is_closed(t)
    # traversal: v0 -> v2 -> v1 -> v0
    assert loop.ordered_vertex_ids(t) == [v0.id, v2.id, v1.id, v0.id]


def test_mixed_orientation_closed():
    # Build a triangle with e1 defined in the opposite direction.
    # (v2 -> v1) to verify that reversed=True corrects the orientation.
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    v2 = t.add_vertex(Point2D(0, 1))
    e0 = t.add_edge(v0, v1, Line(v0.point, v1.point))
    e1 = t.add_edge(v2, v1, Line(v2.point, v1.point))  # ojo, in reverse
    e2 = t.add_edge(v2, v0, Line(v2.point, v0.point))

    loop = Loop()
    loop.add_edge(e0.id)
    loop.add_edge(e1.id, reversed=True)
    loop.add_edge(e2.id)
    assert loop.is_closed(t)
    assert loop.ordered_vertex_ids(t) == [v0.id, v1.id, v2.id, v0.id]


def test_length_triangle():
    t, _, (e0, e1, e2) = make_triangle()
    loop = Loop()
    loop.add_edge(e0.id)
    loop.add_edge(e1.id)
    loop.add_edge(e2.id)
    expected = 1.0 + math.sqrt(2.0) + 1.0
    assert math.isclose(loop.length(t), expected)
