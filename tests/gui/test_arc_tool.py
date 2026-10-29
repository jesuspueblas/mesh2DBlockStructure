import math

from meshcad.core.geometry.arc import Arc
from meshcad.gui.tools.arc_tool import ArcTool


class FakeCanvas:
    def __init__(self):
        self.geometries = []
        self.previews = []
        self.cleared = 0

    def add_geometry(self, geometry):
        self.geometries.append(geometry)

    def snap_to_vertex(self, p):
        return None

    def show_preview(self, geometry):
        self.previews.append(geometry)

    def clear_preview(self):
        self.cleared += 1


class FakeMouseEvent:
    def __init__(self, x, y):
        self._pos = (x, y)

    def pos(self):
        from PyQt5.QtCore import QPoint

        return QPoint(self._pos[0], self._pos[1])


def make_canvas():
    c = FakeCanvas()
    c.mapToScene = lambda qpoint: qpoint  # type: ignore[attr-defined]
    return c


def test_arc_tool_creates_arc_after_three_clicks():
    canvas = make_canvas()
    tool = ArcTool(canvas)
    tool.mouse_press(FakeMouseEvent(0, 0))
    tool.mouse_press(FakeMouseEvent(1, 0))
    tool.mouse_press(FakeMouseEvent(0, 1))
    assert len(canvas.geometries) == 1
    arc = canvas.geometries[0]
    assert isinstance(arc, Arc)
    assert math.isclose(arc.radius, 1.0)
    assert math.isclose(arc.start_angle, 0.0)
    assert math.isclose(arc.end_angle, math.pi / 2)


def test_arc_tool_preview_circle_after_first_click():
    canvas = make_canvas()
    tool = ArcTool(canvas)
    tool.mouse_press(FakeMouseEvent(0, 0))
    tool.mouse_move(FakeMouseEvent(2, 0))
    assert len(canvas.previews) >= 1
    preview = canvas.previews[-1]
    assert isinstance(preview, Arc)
    assert math.isclose(preview.radius, 2.0)


def test_arc_tool_preview_arc_after_second_click():
    canvas = make_canvas()
    tool = ArcTool(canvas)
    tool.mouse_press(FakeMouseEvent(0, 0))  # Center.
    tool.mouse_press(FakeMouseEvent(1, 0))  # Start.
    tool.mouse_move(FakeMouseEvent(0, 1))   # Candidate endpoint.
    preview = canvas.previews[-1]
    assert isinstance(preview, Arc)
    assert math.isclose(preview.radius, 1.0)
    assert math.isclose(preview.start_angle, 0.0)
    assert math.isclose(preview.end_angle, math.pi / 2)
