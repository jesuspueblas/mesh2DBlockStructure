from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtTest import QTest

from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.gui.main_window import MainWindow


def test_canvas_edge_selection_and_control_toggle(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    topology = window.document.topology
    vertices = [
        topology.add_vertex(Point2D(0, 0)),
        topology.add_vertex(Point2D(10, 0)),
        topology.add_vertex(Point2D(0, 5)),
        topology.add_vertex(Point2D(10, 5)),
    ]
    first_edge = topology.add_edge(
        vertices[0], vertices[1], Line(vertices[0].point, vertices[1].point)
    )
    second_edge = topology.add_edge(
        vertices[2], vertices[3], Line(vertices[2].point, vertices[3].point)
    )
    window.document.notify_change()
    window.show()
    qtbot.wait(50)
    window.canvas.reset_zoom()

    def click_scene_point(point, modifiers=Qt.NoModifier):
        viewport_point = window.canvas.mapFromScene(QPointF(point.x, point.y))
        QTest.mouseClick(
            window.canvas.viewport(),
            Qt.LeftButton,
            modifiers,
            viewport_point,
        )

    click_scene_point(Point2D(5, 0))
    assert window.edges_panel.selected_edge_ids() == [first_edge.id]
    assert window.canvas._highlight_item.pen().color() == QColor(0, 190, 230)

    click_scene_point(Point2D(5, 5), Qt.ControlModifier)
    assert set(window.edges_panel.selected_edge_ids()) == {
        first_edge.id,
        second_edge.id,
    }

    click_scene_point(Point2D(5, 0), Qt.ControlModifier)
    assert window.edges_panel.selected_edge_ids() == [second_edge.id]

    click_scene_point(Point2D(5, 0))
    assert window.edges_panel.selected_edge_ids() == [first_edge.id]

    click_scene_point(Point2D(20, 20), Qt.ControlModifier)
    assert window.edges_panel.selected_edge_ids() == [first_edge.id]

    click_scene_point(Point2D(20, 20))
    assert window.edges_panel.selected_edge_ids() == []
    assert window.canvas._highlight_item is None
