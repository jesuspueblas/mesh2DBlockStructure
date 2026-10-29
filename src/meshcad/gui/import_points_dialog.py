"""Preview dialog for importing an ordered point sequence."""

from __future__ import annotations

from collections.abc import Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QVBoxLayout,
)

from meshcad.core.geometry.point import Point2D
from meshcad.core.geometry.spline import Spline


class _FitGraphicsView(QGraphicsView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._fit_rect = None

    def set_fit_rect(self, rect) -> None:
        self._fit_rect = rect
        self.fitInView(rect, Qt.KeepAspectRatio)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fit_rect is not None:
            self.fitInView(self._fit_rect, Qt.KeepAspectRatio)


class ImportPointSequenceDialog(QDialog):
    def __init__(self, points: Sequence[Point2D], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import Point Sequence")
        self.resize(720, 520)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"{len(points)} ordered points will be imported as one spline edge."
        ))

        spline = Spline(tuple(points))
        preview = _FitGraphicsView(self)
        preview.scale(1, -1)
        preview.setRenderHint(QPainter.Antialiasing, True)
        preview.setBackgroundBrush(QColor(250, 250, 252))
        scene = QGraphicsScene(preview)
        preview.setScene(scene)

        path = QPainterPath()
        sample_count = min(max(len(points) * 8, 200), 4000)
        samples = spline.sample(sample_count)
        path.moveTo(samples[0].x, samples[0].y)
        for point in samples[1:]:
            path.lineTo(point.x, point.y)

        curve = QGraphicsPathItem(path)
        curve.setPen(QPen(QColor(30, 90, 200), 0))
        scene.addItem(curve)
        bounds = path.boundingRect()
        margin = max(bounds.width(), bounds.height(), 1.0) * 0.05
        bounds.adjust(-margin, -margin, margin, margin)
        marker_radius = max(bounds.width(), bounds.height()) * 0.008
        start_color = QColor(22, 163, 74)
        scene.addEllipse(
            points[0].x - marker_radius,
            points[0].y - marker_radius,
            marker_radius * 2,
            marker_radius * 2,
            QPen(start_color, 0),
            QBrush(start_color),
        )
        end_color = QColor(220, 38, 38)
        scene.addEllipse(
            points[-1].x - marker_radius,
            points[-1].y - marker_radius,
            marker_radius * 2,
            marker_radius * 2,
            QPen(end_color, 0),
            QBrush(end_color),
        )
        scene.setSceneRect(bounds)
        preview.set_fit_rect(bounds)
        layout.addWidget(preview)

        layout.addWidget(QLabel(
            f"Start: ({points[0].x:g}, {points[0].y:g})    "
            f"End: ({points[-1].x:g}, {points[-1].y:g})"
        ))

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        buttons.button(QDialogButtonBox.Ok).setText("Import")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
