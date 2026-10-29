"""Tool for selecting four corners of a loop."""

from __future__ import annotations

from typing import Callable, List

from meshcad.core.geometry.point import Point2D
from meshcad.gui.tools.base import BaseTool


class CornerPickerTool(BaseTool):
    """Ask the user to click four vertices on the active loop.

    Once all four are selected, call on_complete(vertex_ids).
    """

    def __init__(self, canvas, loop, on_complete: Callable[[List[int]], None]) -> None:
        super().__init__(canvas)
        self.loop = loop
        self.on_complete = on_complete
        self.corners: List[int] = []

    def mouse_press(self, event) -> None:
        pos = self.canvas.mapToScene(event.pos())
        p = Point2D(pos.x(), pos.y())
        vertex = self.canvas.snap_to_vertex(p)
        if vertex is None:
            return

        loop_vertex_ids = self.loop.ordered_vertex_ids(self.canvas.document.topology)
        if vertex.id not in loop_vertex_ids:
            return
        if vertex.id in self.corners:
            return

        self.corners.append(vertex.id)
        self.canvas.flash_vertex(vertex.id)

        if len(self.corners) == 4:
            self.on_complete(list(self.corners))
            self.cancel()

    def cancel(self) -> None:
        self.corners = []
        self.canvas.clear_preview()
