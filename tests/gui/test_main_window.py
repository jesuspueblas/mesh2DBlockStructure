from PyQt5.QtCore import QPointF, Qt

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


def test_main_window_has_mesh_patches_panel(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    assert w.patches_panel.windowTitle() == "Mesh Patches"
    assert w.patches_panel.document is w.document


def test_main_window_has_mesh_json_export_action(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.action_export_cfd_json.text() == "Export Mesh (JSON)..."


def test_split_edge_toolbar_tool_clicks_selected_edge(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    edge = window.canvas.add_geometry(
        Line(Point2D(0, 0), Point2D(4, 0))
    )
    window.edges_panel.select_edges([edge.id])

    qtbot.mouseClick(window.edges_panel.split_button, Qt.LeftButton)

    assert window.action_split_edge.isChecked()
    assert window.canvas.tool is not None
    click_position = window.canvas.mapFromScene(QPointF(2, 0))
    qtbot.mouseClick(
        window.canvas.viewport(), Qt.LeftButton, pos=click_position
    )

    assert len(window.document.topology.edges()) == 2
    assert window.action_select.isChecked()
    assert not window.action_split_edge.isChecked()


def test_split_edge_coordinate_entry(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)
    edge = window.canvas.add_geometry(
        Line(Point2D(0, 0), Point2D(4, 0))
    )
    window.edges_panel.select_edges([edge.id])
    coordinates = iter(((1.5, True), (0.0, True)))
    monkeypatch.setattr(
        "meshcad.gui.edges_panel.QInputDialog.getDouble",
        lambda *args, **kwargs: next(coordinates),
    )

    qtbot.mouseClick(window.edges_panel.split_coordinates_button, Qt.LeftButton)

    assert len(window.document.topology.edges()) == 2
    assert window.edges_panel.status.text() == "Edge split into edges 0 and 1."


def test_cfd_json_export_cancel_does_not_generate_mesh(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)
    window.document.blocks = [object()]
    called = {"generate": False}

    def generate_mesh():
        called["generate"] = True
        return [], []

    monkeypatch.setattr(window.document, "generate_mesh", generate_mesh)
    monkeypatch.setattr(
        "meshcad.gui.main_window.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: ("", ""),
    )
    window._on_export_cfd_json()
    assert called["generate"] is False


def test_cfd_json_export_builds_and_writes_current_mesh(qtbot, monkeypatch, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)
    block = object()
    block_mesh = object()
    cfd_mesh = object()
    window.document.blocks = [block]
    output_without_suffix = tmp_path / "solver-mesh"
    calls = {}

    monkeypatch.setattr(
        window.document, "generate_mesh", lambda: ([block_mesh], [])
    )
    monkeypatch.setattr(
        "meshcad.gui.main_window.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(output_without_suffix), ""),
    )

    def build(meshes, blocks, topology, mesh_model, boundaries):
        calls["build"] = (meshes, blocks, topology, mesh_model, boundaries)
        return cfd_mesh

    def write(path, mesh, boundaries, pretty=False):
        calls["write"] = (path, mesh, boundaries, pretty)

    monkeypatch.setattr("meshcad.gui.main_window.build_cfd_mesh", build)
    monkeypatch.setattr("meshcad.gui.main_window.write_cfd_mesh_json", write)
    window._on_export_cfd_json()

    assert calls["build"][0] == [block_mesh]
    assert calls["build"][1] == [block]
    assert calls["write"][0] == tmp_path / "solver-mesh.json"
    assert calls["write"][1] is cfd_mesh
    assert calls["write"][3] is False
    assert "solver-mesh.json" in window.status_label.text()


def test_cfd_json_export_reports_generation_errors(qtbot, monkeypatch, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)
    window.document.blocks = [object()]
    messages = []
    monkeypatch.setattr(
        "meshcad.gui.main_window.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(tmp_path / "mesh.json"), ""),
    )
    monkeypatch.setattr(
        window.document, "generate_mesh", lambda: ([], ["Block 0 is invalid"])
    )
    monkeypatch.setattr(
        "meshcad.gui.main_window.QMessageBox.critical",
        lambda parent, title, text: messages.append((title, text)),
    )
    window._on_export_cfd_json()
    assert messages == [
        ("CFD Export Error", "Mesh generation failed:\nBlock 0 is invalid")
    ]
