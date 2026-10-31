from PyQt5.QtCore import QPoint, QPointF, Qt
from PyQt5.QtTest import QTest

from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.gui.canvas import CadCanvas
from meshcad.gui.document import Document
from meshcad.gui.tools.zoom_window_tool import ZoomWindowTool


def test_zoom_window_drag_fits_selected_area(qtbot):
    document = Document()
    canvas = CadCanvas(document)
    canvas.resize(900, 600)
    qtbot.addWidget(canvas)
    canvas.add_geometry(Line(Point2D(-100, -100), Point2D(100, 100)))
    canvas.show()
    qtbot.waitExposed(canvas)
    canvas.set_tool(ZoomWindowTool(canvas))
    initial_scale = abs(canvas.transform().m11())
    center = canvas.viewport().rect().center()
    start = center - QPoint(80, 80)
    end = center + QPoint(80, 80)

    QTest.mousePress(canvas.viewport(), Qt.LeftButton, pos=start)
    QTest.mouseMove(canvas.viewport(), end)
    assert canvas.tool._rubber_band is not None
    selected_start = canvas.mapToScene(start)
    selected_end = canvas.mapToScene(end)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, pos=end)

    assert abs(canvas.transform().m11()) > initial_scale
    assert canvas.tool._rubber_band is None
    assert len(document.topology.edges()) == 1
    mapped_center = canvas.mapFromScene(
        QPointF(
            (selected_start.x() + selected_end.x()) / 2,
            (selected_start.y() + selected_end.y()) / 2,
        )
    )
    assert (mapped_center - center).manhattanLength() <= 10
    selected_top = canvas.mapFromScene(
        QPointF(selected_start.x(), selected_start.y())
    )
    selected_bottom = canvas.mapFromScene(
        QPointF(selected_start.x(), selected_end.y())
    )
    assert abs(selected_bottom.y() - selected_top.y()) >= (
        canvas.viewport().height() * 0.8
    )


def test_scene_bounds_expand_when_geometry_changes(qtbot):
    canvas = CadCanvas(Document())
    qtbot.addWidget(canvas)
    canvas.resize(800, 600)
    canvas.show()
    qtbot.waitExposed(canvas)

    canvas.add_geometry(Line(Point2D(10000, 20000), Point2D(11000, 21000)))

    bounds = canvas.scene().sceneRect()
    assert bounds.contains(QPointF(10000, 20000))
    assert bounds.contains(QPointF(11000, 21000))


def test_zoom_window_ignores_tiny_drag(qtbot):
    canvas = CadCanvas(Document())
    qtbot.addWidget(canvas)
    canvas.resize(800, 600)
    canvas.show()
    qtbot.waitExposed(canvas)
    canvas.set_tool(ZoomWindowTool(canvas))
    initial_transform = canvas.transform()
    start = QPoint(200, 200)

    QTest.mousePress(canvas.viewport(), Qt.LeftButton, pos=start)
    QTest.mouseRelease(
        canvas.viewport(), Qt.LeftButton, pos=start + QPoint(2, 2)
    )

    assert canvas.transform() == initial_transform
    assert canvas.tool._rubber_band is None
