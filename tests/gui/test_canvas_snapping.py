import math

from meshcad.core.geometry.point import Point2D
from meshcad.gui.document import Document


def test_snap_to_vertex(qtbot):
    """The canvas must find the closest vertex within the tolerance."""
    from meshcad.gui.canvas import CadCanvas

    doc = Document()
    canvas = CadCanvas(doc)
    qtbot.addWidget(canvas)

    v = doc.topology.add_vertex(Point2D(0.0, 0.0))

    # With the default tolerance, a nearby point must snap to the vertex.
    near = Point2D(0.5, 0.5)
    snapped = canvas.snap_to_vertex(near)
    assert snapped is v


def test_snap_to_vertex_far(qtbot):
    from meshcad.gui.canvas import CadCanvas

    doc = Document()
    canvas = CadCanvas(doc)
    qtbot.addWidget(canvas)

    doc.topology.add_vertex(Point2D(0.0, 0.0))
    far = Point2D(100.0, 100.0)
    assert canvas.snap_to_vertex(far) is None
