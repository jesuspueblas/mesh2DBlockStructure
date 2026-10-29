from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.distribution import UniformDistribution
from meshcad.core.mesh.model import EdgeMeshSpec
from meshcad.gui.canvas import CadCanvas
from meshcad.gui.document import Document
from meshcad.gui.main_window import MainWindow


def test_drawing_geometry_can_be_undone_and_redone(qtbot):
    document = Document()
    canvas = CadCanvas(document)
    qtbot.addWidget(canvas)

    edge = canvas.add_geometry(Line(Point2D(0, 0), Point2D(2, 0)))

    assert document.undo_stack.count() == 1
    assert document.undo_stack.undoText() == "Draw geometry"

    document.undo_stack.undo()

    assert document.topology.edges() == []
    assert document.topology.vertices() == []

    document.undo_stack.redo()

    assert [current.id for current in document.topology.edges()] == [edge.id]
    assert len(document.topology.vertices()) == 2


def test_edge_split_can_be_undone_and_redone(qtbot):
    document = Document()
    qtbot.addWidget(CadCanvas(document))
    start = document.topology.add_vertex(Point2D(0, 0))
    end = document.topology.add_vertex(Point2D(4, 0))
    edge = document.topology.add_edge(start, end, Line(start.point, end.point))
    document.set_edge_spec(EdgeMeshSpec(edge.id, 9, UniformDistribution()))
    document.undo_stack.clear()

    first, second = document.split_edge(edge.id, 0.5)

    assert len(document.topology.edges()) == 2
    assert document.undo_stack.undoText() == "Split edge"
    document.undo_stack.undo()

    assert len(document.topology.edges()) == 1
    assert document.topology.get_edge(edge.id).geometry.start_point() == start.point
    assert document.mesh.get_spec(edge.id).n_nodes == 9

    document.undo_stack.redo()

    assert {current.id for current in document.topology.edges()} == {
        first.id, second.id
    }


def test_edge_distribution_can_be_undone_and_redone():
    document = Document()
    start = document.topology.add_vertex(Point2D(0, 0))
    end = document.topology.add_vertex(Point2D(1, 0))
    edge = document.topology.add_edge(start, end, Line(start.point, end.point))

    document.set_edge_spec(EdgeMeshSpec(edge.id, 8, UniformDistribution()))

    assert document.mesh.get_spec(edge.id).n_nodes == 8
    document.undo_stack.undo()
    assert document.mesh.get_spec(edge.id).n_nodes == 5
    document.undo_stack.redo()
    assert document.mesh.get_spec(edge.id).n_nodes == 8


def test_mesh_patch_changes_can_be_undone_and_redone():
    document = Document()

    patch = document.add_mesh_patch("Walls")
    assert document.patches.get_patch(patch.id).name == "Walls"

    document.undo_stack.undo()
    assert document.patches.patches() == ()

    document.undo_stack.redo()
    assert document.patches.get_patch(patch.id).name == "Walls"


def test_undo_redo_actions_are_available_in_edit_menu(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.canvas.add_geometry(Line(Point2D(0, 0), Point2D(1, 0)))

    assert window.action_undo.isEnabled()
    window.action_undo.trigger()
    assert not window.action_undo.isEnabled()
    assert window.action_redo.isEnabled()

    window.action_redo.trigger()

    assert window.action_undo.isEnabled()
    assert not window.action_redo.isEnabled()


def test_loading_project_clears_undo_history():
    document = Document()
    start = document.add_vertex(Point2D(0, 0))
    assert document.undo_stack.canUndo()

    document.load_from(Document())

    assert not document.undo_stack.canUndo()
    assert not document.topology.has_vertex(start.id)
