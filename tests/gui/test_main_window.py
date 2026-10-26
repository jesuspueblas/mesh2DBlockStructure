from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.gui.document import Document
from meshcad.gui.main_window import MainWindow
from meshcad.io.project_io import load_project


def test_main_window_starts_with_empty_document(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    assert len(w.document.topology.vertices()) == 0
    assert w.current_path is None
    assert "untitled" in w.windowTitle()


def test_main_window_new_clears(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    t = w.document.topology
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    t.add_edge(v0, v1, Line(v0.point, v1.point))
    assert len(w.document.topology.edges()) == 1

    w._on_new()
    assert len(w.document.topology.edges()) == 0
    assert w.current_path is None


def test_main_window_save_and_reload(qtbot, tmp_path):
    w = MainWindow()
    qtbot.addWidget(w)

    t = w.document.topology
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    t.add_edge(v0, v1, Line(v0.point, v1.point))

    path = tmp_path / "proj.json"
    w._save_to(path)
    assert path.exists()
    assert w.current_path == path

    w._on_new()
    assert len(w.document.topology.edges()) == 0

    data = load_project(path)
    loaded = Document.from_dict(data)
    w.document.load_from(loaded)
    assert len(w.document.topology.edges()) == 1


def test_main_window_has_boundary_conditions_panel(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    assert w.boundaries_panel.windowTitle() == "Boundary Conditions"
    assert w.boundaries_panel.document is w.document
