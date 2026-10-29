import pytest

from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.geometry.spline import Spline, SplineSegment
from meshcad.core.topology.topology import Topology


def test_add_vertex_unique_ids():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    assert v0.id == 0
    assert v1.id == 1
    assert v0.id != v1.id


def test_get_vertex():
    t = Topology()
    v = t.add_vertex(Point2D(2, 3))
    assert t.get_vertex(v.id) is v
    assert t.has_vertex(v.id)
    assert not t.has_vertex(999)


def test_get_vertex_missing_raises():
    t = Topology()
    with pytest.raises(KeyError):
        t.get_vertex(42)


def test_find_vertex_at():
    t = Topology()
    v = t.add_vertex(Point2D(1.0, 1.0))
    assert t.find_vertex_at(Point2D(1.0, 1.0)) is v
    assert t.find_vertex_at(Point2D(1.0 + 1e-10, 1.0)) is v
    assert t.find_vertex_at(Point2D(1.5, 1.5)) is None


def test_add_edge_valid():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    e = t.add_edge(v0, v1, Line(v0.point, v1.point))
    assert e.id == 0
    assert e.start_vertex_id == v0.id
    assert e.end_vertex_id == v1.id


def test_add_edge_geometry_must_match_start():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    with pytest.raises(ValueError):
        t.add_edge(v0, v1, Line(Point2D(5, 5), v1.point))


def test_add_edge_geometry_must_match_end():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    with pytest.raises(ValueError):
        t.add_edge(v0, v1, Line(v0.point, Point2D(9, 9)))


def test_add_edge_foreign_vertex_rejected():
    t1 = Topology()
    t2 = Topology()
    v0 = t2.add_vertex(Point2D(0, 0))
    v1 = t2.add_vertex(Point2D(1, 0))
    with pytest.raises(ValueError):
        t1.add_edge(v0, v1, Line(v0.point, v1.point))


def test_edges_unique_ids():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    e0 = t.add_edge(v0, v1, Line(v0.point, v1.point))
    e1 = t.add_edge(v1, v0, Line(v1.point, v0.point))
    assert e0.id != e1.id


def test_edge_ids_remain_monotonic_after_removing_highest_id():
    t = Topology()
    vertices = [t.add_vertex(Point2D(i, 0)) for i in range(3)]
    edges = [
        t.add_edge(vertices[0], vertices[1], Line(vertices[0].point, vertices[1].point)),
        t.add_edge(vertices[1], vertices[2], Line(vertices[1].point, vertices[2].point)),
        t.add_edge(vertices[2], vertices[0], Line(vertices[2].point, vertices[0].point)),
    ]

    t.remove_edge(edges[-1].id)
    next_edge = t.add_edge(
        vertices[0], vertices[2], Line(vertices[0].point, vertices[2].point)
    )

    assert next_edge.id == edges[-1].id + 1


def test_len_and_listing():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    t.add_edge(v0, v1, Line(v0.point, v1.point))
    assert len(t) == 3
    assert len(t.vertices()) == 2
    assert len(t.edges()) == 1


def test_split_edge_preserves_line_geometry_and_original_id():
    topology = Topology()
    start = topology.add_vertex(Point2D(0, 0))
    end = topology.add_vertex(Point2D(4, 0))
    edge = topology.add_edge(start, end, Line(start.point, end.point))

    first, second = topology.split_edge(edge.id, 0.25)

    assert first.id == edge.id
    assert first.geometry.end_point() == Point2D(1, 0)
    assert second.geometry.start_point() == Point2D(1, 0)
    assert second.geometry.end_point() == Point2D(4, 0)


def test_split_edge_preserves_arc_shape():
    from meshcad.core.geometry.arc import Arc
    import math

    topology = Topology()
    geometry = Arc(Point2D(0, 0), 2, 0, math.pi)
    start = topology.add_vertex(geometry.start_point())
    end = topology.add_vertex(geometry.end_point())
    edge = topology.add_edge(start, end, geometry)

    first, second = topology.split_edge(edge.id, 0.4)

    for i in range(11):
        t = i / 10
        if t <= 0.4:
            expected = geometry.evaluate(t)
            actual = first.geometry.evaluate(t / 0.4)
        else:
            expected = geometry.evaluate(t)
            actual = second.geometry.evaluate((t - 0.4) / 0.6)
        assert actual.distance_to(expected) < 1e-9


def test_split_edge_preserves_spline_shape():
    topology = Topology()
    geometry = Spline(
        (Point2D(0, 0), Point2D(1, 2), Point2D(2, -1), Point2D(3, 0))
    )
    start = topology.add_vertex(geometry.start_point())
    end = topology.add_vertex(geometry.end_point())
    edge = topology.add_edge(start, end, geometry)

    first, second = topology.split_edge(edge.id, 0.43)

    assert isinstance(first.geometry, SplineSegment)
    assert isinstance(second.geometry, SplineSegment)
    for i in range(11):
        t = i / 10
        if t <= 0.43:
            expected = geometry.evaluate(t)
            actual = first.geometry.evaluate(t / 0.43)
        else:
            expected = geometry.evaluate(t)
            actual = second.geometry.evaluate((t - 0.43) / 0.57)
        assert actual.distance_to(expected) < 1e-9


def test_split_spline_segments_remain_connected_when_split_vertex_moves():
    topology = Topology()
    geometry = Spline(
        (Point2D(0, 0), Point2D(1, 2), Point2D(2, -1), Point2D(3, 0))
    )
    start = topology.add_vertex(geometry.start_point())
    end = topology.add_vertex(geometry.end_point())
    edge = topology.add_edge(start, end, geometry)
    first, second = topology.split_edge(edge.id, 0.43)
    split_vertex_id = first.end_vertex_id

    moved = Point2D(1.2, 0.3)
    topology.move_vertex(split_vertex_id, moved)

    assert topology.get_edge(first.id).geometry.end_point().distance_to(moved) < 1e-12
    assert topology.get_edge(second.id).geometry.start_point().distance_to(moved) < 1e-12


def test_split_side_preserves_reversed_traversal():
    from meshcad.core.topology.block_side import BlockSide
    from meshcad.core.topology.edge import OrientedEdge

    side = BlockSide((OrientedEdge(2, reversed=True),))
    split = Topology.replace_edge_in_side(side, 2, 5)

    assert split == (OrientedEdge(5, True), OrientedEdge(2, True))
