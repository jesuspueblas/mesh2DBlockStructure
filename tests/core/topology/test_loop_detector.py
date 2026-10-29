from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.topology.loop_detector import find_loops
from meshcad.core.topology.topology import Topology


def make_square():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    v2 = t.add_vertex(Point2D(1, 1))
    v3 = t.add_vertex(Point2D(0, 1))
    t.add_edge(v0, v1, Line(v0.point, v1.point))
    t.add_edge(v1, v2, Line(v1.point, v2.point))
    t.add_edge(v2, v3, Line(v2.point, v3.point))
    t.add_edge(v3, v0, Line(v3.point, v0.point))
    return t


def test_single_square():
    t = make_square()
    loops = find_loops(t)
    assert len(loops) == 1
    assert len(loops[0]) == 4
    assert loops[0].is_closed(t)


def test_open_chain_no_loops():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    v2 = t.add_vertex(Point2D(2, 0))
    t.add_edge(v0, v1, Line(v0.point, v1.point))
    t.add_edge(v1, v2, Line(v1.point, v2.point))
    assert find_loops(t) == []


def test_two_adjacent_squares_share_edge():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    v2 = t.add_vertex(Point2D(2, 0))
    v3 = t.add_vertex(Point2D(0, 1))
    v4 = t.add_vertex(Point2D(1, 1))
    v5 = t.add_vertex(Point2D(2, 1))
    t.add_edge(v0, v1, Line(v0.point, v1.point))
    t.add_edge(v1, v2, Line(v1.point, v2.point))
    t.add_edge(v2, v5, Line(v2.point, v5.point))
    t.add_edge(v5, v4, Line(v5.point, v4.point))
    t.add_edge(v4, v3, Line(v4.point, v3.point))
    t.add_edge(v3, v0, Line(v3.point, v0.point))
    t.add_edge(v1, v4, Line(v1.point, v4.point))  # edge shared

    loops = find_loops(t)
    # It must find at least the two squares and the outer rectangle.
    assert len(loops) >= 2
    for loop in loops:
        assert loop.is_closed(t)
