"""Split one selected edge at the nearest point to a canvas click."""

from PyQt5.QtCore import Qt

from meshcad.core.geometry.point import Point2D
from meshcad.gui.tools.base import BaseTool


class SplitEdgeTool(BaseTool):
    def __init__(self, canvas, edge_id, on_complete, on_error) -> None:
        super().__init__(canvas)
        self.edge_id = edge_id
        self.on_complete = on_complete
        self.on_error = on_error

    def mouse_press(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return

        position = self.canvas.mapToScene(event.pos())
        point = Point2D(position.x(), position.y())
        try:
            parameter, _, distance = (
                self.canvas.document.topology.closest_point_on_edge(
                    self.edge_id, point
                )
            )
            scale = abs(self.canvas.transform().m11())
            if distance * scale > 8.0:
                raise ValueError("Click close to the selected edge to split it.")
            edges = self.canvas.document.split_edge(self.edge_id, parameter)
        except (KeyError, TypeError, ValueError) as error:
            self.canvas.set_tool(None)
            self.on_error(str(error))
            return

        self.canvas.set_tool(None)
        self.on_complete(edges)
