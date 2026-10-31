"""Zoom to a rectangle drawn on the canvas."""

from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import QGraphicsRectItem

from meshcad.gui.tools.base import BaseTool


class ZoomWindowTool(BaseTool):
    def __init__(self, canvas) -> None:
        super().__init__(canvas)
        self._start_pos = None
        self._rubber_band = None

    def mouse_press(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        self._start_pos = event.pos()
        start = self.canvas.mapToScene(self._start_pos)
        self._rubber_band = QGraphicsRectItem(QRectF(start, start))
        pen = QPen(QColor("#2563EB"), 1.0, Qt.DashLine)
        pen.setCosmetic(True)
        self._rubber_band.setPen(pen)
        self._rubber_band.setBrush(QBrush(QColor(37, 99, 235, 35)))
        self._rubber_band.setZValue(10000)
        self.canvas.scene().addItem(self._rubber_band)

    def mouse_move(self, event) -> None:
        if self._start_pos is None or self._rubber_band is None:
            return
        start = self.canvas.mapToScene(self._start_pos)
        end = self.canvas.mapToScene(event.pos())
        self._rubber_band.setRect(QRectF(start, end).normalized())

    def mouse_release(self, event) -> None:
        if event.button() != Qt.LeftButton or self._start_pos is None:
            return

        start_pos = self._start_pos
        end_pos = event.pos()
        rect = None
        if abs(end_pos.x() - start_pos.x()) >= 5 and abs(
            end_pos.y() - start_pos.y()
        ) >= 5:
            start = self.canvas.mapToScene(start_pos)
            end = self.canvas.mapToScene(end_pos)
            rect = QRectF(start, end).normalized()

        self._remove_rubber_band()
        if rect is not None:
            self.canvas.zoom_to_rect(rect)

    def cancel(self) -> None:
        self._start_pos = None
        self._remove_rubber_band()

    def _remove_rubber_band(self) -> None:
        if self._rubber_band is not None:
            self.canvas.scene().removeItem(self._rubber_band)
            self._rubber_band = None
        self._start_pos = None
