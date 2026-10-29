from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.gui.canvas import CadCanvas
from meshcad.gui.document import Document


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


def test_dragging_vertex_snaps_and_merges_on_release(qtbot):
    from PyQt5.QtGui import QColor

    doc = Document()
    canvas = CadCanvas(doc)
    qtbot.addWidget(canvas)
    topology = doc.topology
    source = topology.add_vertex(Point2D(0, 0))
    source_end = topology.add_vertex(Point2D(-2, 0))
    target = topology.add_vertex(Point2D(5, 0))
    target_end = topology.add_vertex(Point2D(5, 2))
    source_edge = topology.add_edge(
        source, source_end, Line(source.point, source_end.point)
    )
    target_edge = topology.add_edge(
        target, target_end, Line(target.point, target_end.point)
    )
    doc.notify_change()
    canvas.show()
    qtbot.wait(20)
    canvas.reset_zoom()

    source_position = canvas.mapFromScene(QPointF(source.point.x, source.point.y))
    target_position = canvas.mapFromScene(QPointF(target.point.x, target.point.y))
    near_target_position = target_position + QPoint(4, 0)
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, pos=source_position)
    assert canvas._drag_target == ('vertex', source.id)
    move_event = QMouseEvent(
        QEvent.MouseMove,
        QPointF(near_target_position),
        Qt.NoButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    QApplication.sendEvent(canvas.viewport(), move_event)
    assert canvas._snap_target_id == target.id
    assert canvas._vertex_items[target.id].brush().color() == QColor(180, 255, 200)

    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, pos=near_target_position)

    assert not topology.has_vertex(source.id)
    assert topology.get_edge(source_edge.id).start_vertex_id == target.id
    assert topology.get_edge(source_edge.id).geometry.start_point() == target.point
    assert topology.get_edge(target_edge.id).start_vertex_id == target.id
    assert canvas._snap_target_id is None
    assert canvas._vertex_items[target.id].brush().color() == QColor(255, 220, 220)
    assert doc.undo_stack.count() == 1
    assert doc.undo_stack.undoText() == "Merge vertices"

    doc.undo_stack.undo()

    assert doc.topology.has_vertex(source.id)
    assert doc.topology.get_edge(source_edge.id).start_vertex_id == source.id
    assert canvas._vertex_items[target.id].brush().color() != QColor(180, 255, 200)

    doc.undo_stack.redo()

    assert not doc.topology.has_vertex(source.id)
    assert doc.topology.get_edge(source_edge.id).start_vertex_id == target.id


def test_drag_snap_target_ignores_connected_vertex_and_distant_targets(qtbot):
    from meshcad.core.geometry.line import Line

    doc = Document()
    canvas = CadCanvas(doc)
    qtbot.addWidget(canvas)
    topology = doc.topology
    source = topology.add_vertex(Point2D(0, 0))
    connected = topology.add_vertex(Point2D(1, 0))
    distant = topology.add_vertex(Point2D(100, 100))
    topology.add_edge(source, connected, Line(source.point, connected.point))
    canvas.reset_zoom()

    assert canvas._vertex_drag_snap_target(source.id, connected.point) is None
    assert canvas._vertex_drag_snap_target(
        source.id, Point2D(distant.point.x - 10, distant.point.y)
    ) is None


def test_clicking_near_another_vertex_does_not_merge_without_drag(qtbot):
    doc = Document()
    canvas = CadCanvas(doc)
    qtbot.addWidget(canvas)
    source = doc.topology.add_vertex(Point2D(0, 0))
    nearby = doc.topology.add_vertex(Point2D(0.01, 0))
    doc.notify_change()
    canvas.show()
    qtbot.wait(20)
    canvas.reset_zoom()

    click_position = canvas.mapFromScene(QPointF(source.point.x, source.point.y))
    QTest.mouseClick(canvas.viewport(), Qt.LeftButton, pos=click_position)

    assert doc.topology.has_vertex(source.id)
    assert doc.topology.has_vertex(nearby.id)
    assert doc.undo_stack.count() == 0
