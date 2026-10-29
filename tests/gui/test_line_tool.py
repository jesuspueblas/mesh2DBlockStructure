from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.gui.tools.line_tool import LineTool


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


def test_line_tool_creates_line_after_two_clicks():
    canvas = make_canvas()
    tool = LineTool(canvas)
    tool.mouse_press(FakeMouseEvent(0, 0))
    tool.mouse_press(FakeMouseEvent(10, 5))
    assert len(canvas.geometries) == 1
    geom = canvas.geometries[0]
    assert isinstance(geom, Line)
    assert geom.start == Point2D(0, 0)
    assert geom.end == Point2D(10, 5)


def test_line_tool_preview_after_first_click():
    canvas = make_canvas()
    tool = LineTool(canvas)
    tool.mouse_press(FakeMouseEvent(0, 0))
    # A preview must be visible after the first click.
    assert len(canvas.previews) == 1
    # Moving the pointer updates the preview.
    tool.mouse_move(FakeMouseEvent(5, 5))
    assert len(canvas.previews) == 2
    assert canvas.previews[-1].end == Point2D(5, 5)


def test_line_tool_clears_preview_after_completion():
    canvas = make_canvas()
    tool = LineTool(canvas)
    tool.mouse_press(FakeMouseEvent(0, 0))
    cleared_before = canvas.cleared
    tool.mouse_press(FakeMouseEvent(10, 0))
    assert canvas.cleared > cleared_before


def test_line_tool_cancel_clears_preview():
    canvas = make_canvas()
    tool = LineTool(canvas)
    tool.mouse_press(FakeMouseEvent(0, 0))
    tool.cancel()
    assert tool.points == []
    assert canvas.cleared >= 1
