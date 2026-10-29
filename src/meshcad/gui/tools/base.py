"""Base class for interactive tools."""

from __future__ import annotations

from typing import List

from meshcad.core.geometry.point import Point2D


class BaseTool:
    """Common interface for all interactive tools.

    Each tool accumulates points in self.points. Once enough points have
    been collected, it calls canvas.add_geometry. Until then, it displays
    a preview by calling canvas.show_preview.
    """

    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.points: List[Point2D] = []

    def mouse_press(self, event) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def mouse_move(self, event) -> None:
        self._refresh_preview(event)

    def cancel(self) -> None:
        self.points = []
        self.canvas.clear_preview()

    # ----------------------- utilities for subclasses ------------------ #

    def _scene_point(self, event) -> Point2D:
        pos = self.canvas.mapToScene(event.pos())
        p = Point2D(pos.x(), pos.y())
        snapped = self.canvas.snap_to_vertex(p)
        if snapped is not None:
            return snapped.point
        return p

    def _refresh_preview(self, event) -> None:
        """Override this method in each tool."""
        return None
