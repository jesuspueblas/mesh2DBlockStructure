"""Interactive tool for drawing splines."""

from __future__ import annotations

from PyQt5.QtCore import Qt

from meshcad.core.geometry.spline import Spline
from meshcad.gui.tools.base import BaseTool


class SplineTool(BaseTool):
    """Use left-clicks to add points and right-click to finish.

    Show the spline in real time as points are added and the pointer moves.
    """

    def mouse_press(self, event) -> None:
        if event.button() == Qt.RightButton:
            if len(self.points) >= 2:
                self.canvas.add_geometry(Spline(tuple(self.points)))
            self.points = []
            self.canvas.clear_preview()
            return

        p = self._scene_point(event)
        self.points.append(p)
        self._refresh_preview(event)

    def _refresh_preview(self, event) -> None:
        if not self.points:
            self.canvas.clear_preview()
            return
        p = self._scene_point(event)
        pts = tuple(self.points + [p])
        if len(pts) >= 2:
            self.canvas.show_preview(Spline(pts))
