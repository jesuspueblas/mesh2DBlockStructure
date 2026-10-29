"""Interactive tool for drawing line segments."""

from __future__ import annotations

from meshcad.core.geometry.line import Line
from meshcad.gui.tools.base import BaseTool


class LineTool(BaseTool):
    """Two clicks: start and end. Show the line in real time."""

    def mouse_press(self, event) -> None:
        p = self._scene_point(event)
        self.points.append(p)

        if len(self.points) == 2:
            self.canvas.add_geometry(Line(self.points[0], self.points[1]))
            self.points = []
            self.canvas.clear_preview()
        else:
            self._refresh_preview(event)

    def _refresh_preview(self, event) -> None:
        if not self.points:
            self.canvas.clear_preview()
            return
        p = self._scene_point(event)
        self.canvas.show_preview(Line(self.points[0], p))
