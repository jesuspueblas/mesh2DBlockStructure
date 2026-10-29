from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.topology.topology import Topology


def test_remove_edge_deletes_orphaned_vertices():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    e = t.add_edge(v0, v1, Line(v0.point, v1.point))
    
    assert len(t.vertices()) == 2
    t.remove_edge(e.id)
    assert len(t.edges()) == 0
    assert len(t.vertices()) == 0


def test_remove_edge_keeps_shared_vertices():
    t = Topology()
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    v2 = t.add_vertex(Point2D(2, 0))
    e0 = t.add_edge(v0, v1, Line(v0.point, v1.point))
    e1 = t.add_edge(v1, v2, Line(v1.point, v2.point))
    
    assert len(t.vertices()) == 3
    t.remove_edge(e0.id)
    assert len(t.edges()) == 1
    
    # v1 is still used by e1 and must not be deleted; v0 must be deleted.
    v_ids = [v.id for v in t.vertices()]
    assert v0.id not in v_ids
    assert v1.id in v_ids
    assert v2.id in v_ids
