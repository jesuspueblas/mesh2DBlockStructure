from PyQt5.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsView,
    QLabel,
)

from meshcad.core.geometry.point import Point2D
from meshcad.gui.import_points_dialog import ImportPointSequenceDialog


def test_import_preview_shows_one_curve_and_endpoint_summary(qtbot):
    points = [Point2D(0, 0), Point2D(1, 2), Point2D(3, 1)]
    dialog = ImportPointSequenceDialog(points)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(10)

    preview = dialog.findChild(QGraphicsView)
    assert preview is not None
    assert preview.scene() is not None
    assert preview.transform().m11() > 1
    assert preview.transform().m22() < 0
    assert len(preview.scene().items()) == 3
    assert sum(
        isinstance(item, QGraphicsPathItem) for item in preview.scene().items()
    ) == 1
    markers = [
        item for item in preview.scene().items()
        if isinstance(item, QGraphicsEllipseItem)
    ]
    assert len(markers) == 2
    assert all(item.rect().width() < 0.2 for item in markers)
    labels = [label.text() for label in dialog.findChildren(QLabel)]
    assert any("3 ordered points" in text for text in labels)
    assert any("Start: (0, 0)    End: (3, 1)" in text for text in labels)
