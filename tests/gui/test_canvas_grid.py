from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import QGraphicsEllipseItem

from meshcad.core.geometry.point import Point2D
from meshcad.core.geometry.spline import Spline
from meshcad.gui.canvas import CadCanvas
from meshcad.gui.document import Document


def test_toggle_grid(qtbot):
    doc = Document()
    canvas = CadCanvas(doc)
    qtbot.addWidget(canvas)
    assert canvas.show_grid is True
    canvas.show_grid = False
    assert canvas.show_grid is False


def test_vertex_markers_keep_screen_size_when_zooming(qtbot):
    doc = Document()
    vertex = doc.topology.add_vertex(Point2D(0.001, 0.002))
    end = doc.topology.add_vertex(Point2D(0.002, 0.002))
    spline = Spline(
        (vertex.point, Point2D(0.0015, 0.003), end.point)
    )
    doc.topology.add_edge(vertex, end, spline)
    canvas = CadCanvas(doc)
    qtbot.addWidget(canvas)
    canvas._redraw_all()

    item = canvas._vertex_items[vertex.id]
    assert item.flags() & QGraphicsEllipseItem.ItemIgnoresTransformations
    assert item.pos().x() == vertex.point.x
    assert item.pos().y() == vertex.point.y
    assert item.rect().width() == 8.0
    assert item.rect().height() == 8.0
    grip = canvas._grip_items[0]
    assert grip.flags() & QGraphicsEllipseItem.ItemIgnoresTransformations
    assert grip.pos().x() == 0.0015
    assert grip.pos().y() == 0.003
    assert grip.rect().width() == 7.0
    assert grip.rect().height() == 7.0


def test_grid_pen_keeps_pixel_width_when_zooming(qtbot):
    canvas = CadCanvas(Document())
    qtbot.addWidget(canvas)
    image = QImage(100, 100, QImage.Format_ARGB32)
    painter = QPainter(image)

    canvas.drawBackground(painter, QRectF(-10, -10, 20, 20))
    pen = painter.pen()
    painter.end()

    assert pen.isCosmetic()
    assert pen.widthF() == 0.5
