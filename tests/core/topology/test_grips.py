import math

from meshcad.core.geometry.arc import Arc
from meshcad.core.geometry.point import Point2D
from meshcad.core.topology.topology import Topology


def test_move_arc_endpoint_reconnects():
    t = Topology()
    v0 = t.add_vertex(Point2D(1, 0))
    v1 = t.add_vertex(Point2D(0, 1))
    arc = Arc(Point2D(0, 0), 1.0, 0.0, math.pi / 2)
    e = t.add_edge(v0, v1, arc)

    # Move v0 to (2, 0).
    t.move_vertex(v0.id, Point2D(2, 0))
    new_arc = t.get_edge(e.id).geometry
    
    assert isinstance(new_arc, Arc)
    # The arc must pass through both vertices.
    assert math.isclose(new_arc.start_point().distance_to(Point2D(2, 0)), 0.0, abs_tol=1e-7)
    assert math.isclose(new_arc.end_point().distance_to(Point2D(0, 1)), 0.0, abs_tol=1e-7)
