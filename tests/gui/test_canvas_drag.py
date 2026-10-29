from meshcad.core.geometry.arc import Arc
from meshcad.core.geometry.point import Point2D
from meshcad.gui.canvas import CadCanvas
from meshcad.gui.document import Document
import math


def test_dragging_vertex(qtbot):
    doc = Document()
    canvas = CadCanvas(doc)
    qtbot.addWidget(canvas)
    v = doc.topology.add_vertex(Point2D(0, 0))

    # Simulate drag start
    canvas._drag_target = ('vertex', v.id)
    # Move
    doc.topology.move_vertex(v.id, Point2D(10, 10))
    doc.notify_change()

    assert doc.topology.get_vertex(v.id).point == Point2D(10, 10)


def test_auto_mesh_regen(qtbot):
    from meshcad.core.geometry.line import Line
    from meshcad.core.mesh.distribution import UniformDistribution
    from meshcad.core.mesh.model import EdgeMeshSpec
    from meshcad.core.topology.block import Block
    from meshcad.core.topology.loop import Loop

    doc = Document()
    canvas = CadCanvas(doc)
    qtbot.addWidget(canvas)
    t = doc.topology
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    v2 = t.add_vertex(Point2D(1, 1))
    v3 = t.add_vertex(Point2D(0, 1))
    e0 = t.add_edge(v0, v1, Line(v0.point, v1.point))
    e1 = t.add_edge(v1, v2, Line(v1.point, v2.point))
    e2 = t.add_edge(v2, v3, Line(v2.point, v3.point))
    e3 = t.add_edge(v3, v0, Line(v3.point, v0.point))
    loop = Loop()
    for e in (e0, e1, e2, e3):
        loop.add_edge(e.id)
    sides = loop.split_at_corners(t, [v0.id, v1.id, v2.id, v3.id])
    doc.add_block(Block(doc.next_block_id(), sides))
    for e in (e0, e1, e2, e3):
        doc.set_edge_spec(EdgeMeshSpec(e.id, 4, UniformDistribution()))

    doc.generate_mesh()
    assert len(doc.block_meshes) == 1
    old_mesh = doc.block_meshes[0]

    # Moving a vertex should regenerate the mesh automatically.
    doc.topology.move_vertex(v1.id, Point2D(2, 0))
    doc.notify_change()

    assert len(doc.block_meshes) == 1
    new_mesh = doc.block_meshes[0]
    assert new_mesh is not old_mesh
    assert new_mesh.grid[0][-1].x == 2.0
