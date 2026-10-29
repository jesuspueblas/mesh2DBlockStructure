from meshcad.gui.canvas import CadCanvas
from meshcad.gui.document import Document
from PyQt5.QtCore import QPoint


def test_y_axis_flip(qtbot):
    doc = Document()
    canvas = CadCanvas(doc)
    qtbot.addWidget(canvas)
    # The Y-axis must point upward (the transform scales Y by -1).
    assert canvas.transform().m22() == -1.0


def test_grid_spacing_property(qtbot):
    doc = Document()
    canvas = CadCanvas(doc)
    qtbot.addWidget(canvas)
    assert canvas.grid_spacing == 10.0
    canvas.grid_spacing = 5.0
    assert canvas.grid_spacing == 5.0
