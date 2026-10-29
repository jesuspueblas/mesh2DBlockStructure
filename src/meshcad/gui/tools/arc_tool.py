"""Interactive tool for drawing circular arcs."""

from __future__ import annotations

import math

from meshcad.core.geometry.arc import Arc
from meshcad.gui.tools.base import BaseTool

EPS = 1e-9


class ArcTool(BaseTool):
    """Three clicks: center, start, end. Counterclockwise arc with preview.

    - With one point (center), show a circle whose radius follows the pointer.
    - With two points (center, start), show an arc ending at the pointer.
    """

    def mouse_press(self, event) -> None:
        p = self._scene_point(event)
        self.points.append(p)

        if len(self.points) == 3:
            center, start, end = self.points
            radius = center.distance_to(start)
            if radius > EPS:
                a0 = math.atan2(start.y - center.y, start.x - center.x)
                a1 = math.atan2(end.y - center.y, end.x - center.x)
                self.canvas.add_geometry(Arc(center, radius, a0, a1))
            self.points = []
            self.canvas.clear_preview()
        else:
            self._refresh_preview(event)

    def _refresh_preview(self, event) -> None:
        if not self.points:
            self.canvas.clear_preview()
            return

        p = self._scene_point(event)

        if len(self.points) == 1:
            center = self.points[0]
            r = center.distance_to(p)
            if r < EPS:
                self.canvas.clear_preview()
                return
            # Approximate a full circle with an angle just under 2*pi.
            self.canvas.show_preview(Arc(center, r, 0.0, 2.0 * math.pi - 1e-6))
            return

        # len == 2
        center, start = self.points
        r = center.distance_to(start)
        if r < EPS:
            self.canvas.clear_preview()
            return
        a0 = math.atan2(start.y - center.y, start.x - center.x)
        a1 = math.atan2(p.y - center.y, p.x - center.x)
        self.canvas.show_preview(Arc(center, r, a0, a1))
