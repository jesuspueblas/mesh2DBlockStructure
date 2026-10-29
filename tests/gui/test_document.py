import math

import pytest

from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.geometry.spline import Spline
from meshcad.core.mesh.distribution import UniformDistribution
from meshcad.core.mesh.model import EdgeMeshSpec
from meshcad.core.topology.block import Block
from meshcad.core.topology.loop import Loop
from meshcad.core.topology.topology import Topology
from meshcad.gui.boundaries_panel import BoundariesPanel
from meshcad.gui.document import Document
from meshcad.gui.edges_panel import EdgesPanel


def build_square_block(doc, n_nodes=4):
    t = doc.topology
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    v2 = t.add_vertex(Point2D(1, 1))
    v3 = t.add_vertex(Point2D(0, 1))
    e0 = t.add_edge(v0, v1, Line(v0.point, v1.point))
    e1 = t.add_edge(v1, v2, Line(v1.point, v2.point))
    e2 = t.add_edge(v2, v3, Line(v2.point, v3.point))
    e3 = t.add_edge(v3, v0, Line(v3.point, v0.point))

    loop = Loop()
    for e in (e0, e1, e2, e3):
        loop.add_edge(e.id)

    sides = loop.split_at_corners(t, [v0.id, v1.id, v2.id, v3.id])
    block = Block(doc.next_block_id(), sides)
    doc.add_block(block)

    for e in (e0, e1, e2, e3):
        doc.set_edge_spec(EdgeMeshSpec(e.id, n_nodes, UniformDistribution()))
    return block


def test_generate_mesh_no_blocks(qtbot):
    doc = Document()
    meshes, errors = doc.generate_mesh()
    assert meshes == []
    assert errors == []


def test_generate_mesh_single_block(qtbot):
    doc = Document()
    build_square_block(doc, n_nodes=5)
    meshes, errors = doc.generate_mesh()
    assert len(meshes) == 1
    assert errors == []
    assert meshes[0].n_u == 5
    assert meshes[0].n_v == 5


def test_generate_mesh_emits_signal(qtbot):
    doc = Document()
    build_square_block(doc, n_nodes=4)
    with qtbot.waitSignal(doc.mesh_generated, timeout=1000):
        doc.generate_mesh()


def test_generate_mesh_reports_mismatch(qtbot):
    doc = Document()
    t = doc.topology
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    v2 = t.add_vertex(Point2D(1, 1))
    v3 = t.add_vertex(Point2D(0, 1))
    e0 = t.add_edge(v0, v1, Line(v0.point, v1.point))
    e1 = t.add_edge(v1, v2, Line(v1.point, v2.point))
    e2 = t.add_edge(v2, v3, Line(v2.point, v3.point))
    e3 = t.add_edge(v3, v0, Line(v3.point, v0.point))

    loop = Loop()
    for e in (e0, e1, e2, e3):
        loop.add_edge(e.id)
    sides = loop.split_at_corners(t, [v0.id, v1.id, v2.id, v3.id])
    doc.add_block(Block(doc.next_block_id(), sides))

    # Mismatch on sides 0/2 (set directly to bypass propagation).
    doc.mesh.set_spec(EdgeMeshSpec(e0.id, 4, UniformDistribution()))
    doc.mesh.set_spec(EdgeMeshSpec(e2.id, 6, UniformDistribution()))
    doc.mesh.set_spec(EdgeMeshSpec(e1.id, 4, UniformDistribution()))
    doc.mesh.set_spec(EdgeMeshSpec(e3.id, 4, UniformDistribution()))
    doc.recompute_blocks()

    meshes, errors = doc.generate_mesh()
    assert meshes == []
    assert len(errors) == 1
    assert "Block 0" in errors[0]


def test_document_patch_model_round_trip_and_version_3(qtbot):
    doc = Document()
    patch = doc.patches.add_patch("inlet")
    doc.patches.assign_edges(patch.id, [10, 11])

    data = doc.to_dict()
    restored = Document.from_dict(data)

    assert data["version"] == 3
    assert restored.patches.patches() == doc.patches.patches()


def test_document_rejects_internal_edge_patch_assignment(qtbot):
    doc = Document()
    topology = doc.topology
    vertices = [
        topology.add_vertex(Point2D(*point))
        for point in ((0, 0), (1, 0), (1, 1), (0, 1), (2, 0), (2, 1))
    ]
    v0, v1, v2, v3, v4, v5 = vertices
    edges = [
        topology.add_edge(v0, v1, Line(v0.point, v1.point)),
        topology.add_edge(v1, v2, Line(v1.point, v2.point)),
        topology.add_edge(v2, v3, Line(v2.point, v3.point)),
        topology.add_edge(v3, v0, Line(v3.point, v0.point)),
        topology.add_edge(v1, v4, Line(v1.point, v4.point)),
        topology.add_edge(v4, v5, Line(v4.point, v5.point)),
        topology.add_edge(v5, v2, Line(v5.point, v2.point)),
    ]

    left_loop = Loop()
    for edge in edges[:4]:
        left_loop.add_edge(edge.id)
    right_loop = Loop()
    for edge in edges[4:]:
        right_loop.add_edge(edge.id)
    right_loop.add_edge(edges[1].id, reversed=True)
    doc.add_block(
        Block(
            doc.next_block_id(),
            left_loop.split_at_corners(topology, [v.id for v in (v0, v1, v2, v3)]),
        )
    )
    doc.add_block(
        Block(
            doc.next_block_id(),
            right_loop.split_at_corners(topology, [v.id for v in (v1, v4, v5, v2)]),
        )
    )

    patch = doc.add_mesh_patch("wall")
    with pytest.raises(ValueError, match="Only exterior block edges"):
        doc.assign_mesh_patch_edges(patch.id, [edges[1].id])

    assert doc.patches.get_patch(patch.id).edge_ids == ()


def test_document_accepts_exterior_edge_patch_assignment(qtbot):
    doc = Document()
    block = build_square_block(doc)
    exterior_edge_id = block.sides[0].edge_ids()[0]
    patch = doc.add_mesh_patch("wall")

    doc.assign_mesh_patch_edges(patch.id, [exterior_edge_id])

    assert doc.patches.get_patch(patch.id).edge_ids == (exterior_edge_id,)


def test_split_edge_preserves_block_patch_and_mesh(qtbot):
    doc = Document()
    block = build_square_block(doc, n_nodes=5)
    edge_id = block.sides[0].edge_ids()[0]
    patch = doc.add_mesh_patch("wall")
    doc.assign_mesh_patch_edges(patch.id, [edge_id])

    first, second = doc.split_edge_at_point(edge_id, Point2D(0.4, 0))

    assert block.sides[0].edge_ids() == [first.id, second.id]
    assert doc.patches.get_patch(patch.id).edge_ids == (first.id, second.id)
    assert doc.mesh.side_node_count(block.sides[0]) == 6
    assert block.sides[2].node_count == 6
    meshes, errors = doc.generate_mesh()
    assert errors == []
    assert len(meshes) == 1


def test_split_edge_rejects_points_off_edge_without_mutating_document(qtbot):
    doc = Document()
    edge = build_square_block(doc).sides[0].oriented_edges[0]
    with pytest.raises(ValueError, match="must lie on the selected edge"):
        doc.split_edge_at_point(edge.edge_id, Point2D(0.5, 0.5), tolerance=1e-6)
    assert len(doc.topology.edges()) == 4


def test_split_spline_round_trips_project_geometry(qtbot):
    doc = Document()
    points = (Point2D(0, 0), Point2D(1, 2), Point2D(2, 0))
    edge = doc.add_point_sequence(points)
    doc.split_edge(edge.id, 0.4)

    restored = Document.from_dict(doc.to_dict())

    assert len(restored.topology.edges()) == 2
    for current, loaded in zip(doc.topology.edges(), restored.topology.edges()):
        for i in range(11):
            parameter = i / 10
            assert current.geometry.evaluate(parameter).distance_to(
                loaded.geometry.evaluate(parameter)
            ) < 1e-12


def test_split_shared_edge_updates_both_block_traversals(qtbot):
    doc = Document()
    topology = doc.topology
    vertices = [
        topology.add_vertex(Point2D(*point))
        for point in (
            (0, 0), (1, 0), (1, 1), (0, 1), (2, 0), (2, 1)
        )
    ]
    v0, v1, v2, v3, v4, v5 = vertices
    edges = [
        topology.add_edge(v0, v1, Line(v0.point, v1.point)),
        topology.add_edge(v1, v2, Line(v1.point, v2.point)),
        topology.add_edge(v2, v3, Line(v2.point, v3.point)),
        topology.add_edge(v3, v0, Line(v3.point, v0.point)),
        topology.add_edge(v1, v4, Line(v1.point, v4.point)),
        topology.add_edge(v4, v5, Line(v4.point, v5.point)),
        topology.add_edge(v5, v2, Line(v5.point, v2.point)),
    ]
    left_loop = Loop()
    for edge in edges[:4]:
        left_loop.add_edge(edge.id)
    right_loop = Loop()
    for edge in edges[4:]:
        right_loop.add_edge(edge.id)
    right_loop.add_edge(edges[1].id, reversed=True)
    left_block = Block(
        doc.next_block_id(),
        left_loop.split_at_corners(topology, [v.id for v in (v0, v1, v2, v3)]),
    )
    right_block = Block(
        doc.next_block_id(),
        right_loop.split_at_corners(topology, [v.id for v in (v1, v4, v5, v2)]),
    )
    doc.add_block(left_block)
    doc.add_block(right_block)
    for edge in edges:
        doc.mesh.set_spec(EdgeMeshSpec(edge.id, 5, UniformDistribution()))

    first, second = doc.split_edge_at_point(edges[1].id, Point2D(1, 0.4))

    assert left_block.sides[1].edge_ids() == [first.id, second.id]
    assert right_block.sides[3].edge_ids() == [second.id, first.id]
    assert right_block.sides[3].oriented_edges[0].reversed
    meshes, errors = doc.generate_mesh()
    assert errors == []
    assert len(meshes) == 2


def test_split_edge_on_five_edge_loop_preserves_mesh(qtbot):
    doc = Document()
    topology = doc.topology
    vertices = [
        topology.add_vertex(Point2D(*point))
        for point in ((0, 0), (2, 0), (4, 1), (3, 3), (0, 3))
    ]
    edges = [
        topology.add_edge(
            vertices[index],
            vertices[(index + 1) % len(vertices)],
            Line(
                vertices[index].point,
                vertices[(index + 1) % len(vertices)].point,
            ),
        )
        for index in range(len(vertices))
    ]
    loop = Loop()
    for edge in edges:
        loop.add_edge(edge.id)
    block = Block(
        doc.next_block_id(),
        loop.split_at_corners(
            topology, [vertices[index].id for index in (0, 1, 2, 3)]
        ),
    )
    doc.add_block(block)
    for edge in edges:
        doc.mesh.set_spec(EdgeMeshSpec(edge.id, 50, UniformDistribution()))
    doc.mesh.set_spec(EdgeMeshSpec(edges[3].id, 25, UniformDistribution()))
    doc.mesh.set_spec(EdgeMeshSpec(edges[4].id, 26, UniformDistribution()))
    doc.recompute_blocks()

    first, second = doc.split_edge_at_point(
        edges[2].id, edges[2].geometry.evaluate(0.75)
    )

    assert block.sides[2].edge_ids() == [first.id, second.id]
    assert block.sides[0].node_count == block.sides[2].node_count
    assert block.sides[1].node_count == block.sides[3].node_count
    meshes, errors = doc.generate_mesh()
    assert len(meshes) == 1
    assert errors == []


def test_split_edge_uses_next_id_after_highest_edge_was_removed(qtbot):
    doc = Document()
    block = build_square_block(doc, n_nodes=50)
    topology = doc.topology
    extra_start = topology.add_vertex(Point2D(3, 3))
    extra_end = topology.add_vertex(Point2D(4, 3))
    topology.add_edge(
        extra_start, extra_end, Line(extra_start.point, extra_end.point)
    )
    highest = topology.add_edge(
        extra_end,
        topology.add_vertex(Point2D(5, 3)),
        Line(extra_end.point, Point2D(5, 3)),
    )
    topology.remove_edge(highest.id)

    first, second = doc.split_edge_at_point(
        block.sides[0].edge_ids()[0], Point2D(0.5, 0)
    )

    assert second.id == highest.id + 1
    assert doc.mesh.get_spec(second.id).n_nodes >= 2
    assert doc.generate_mesh()[1] == []


def test_set_edge_spec_on_shared_edge_balances_all_adjacent_blocks(qtbot):
    doc = Document()
    topology = doc.topology
    vertices = {
        name: topology.add_vertex(Point2D(*point))
        for name, point in {
            "bottom_left": (0, 0),
            "bottom_mid": (0, 0.5),
            "top_left": (0, 1),
            "bottom_shared": (1, 0),
            "top_shared": (1, 1),
            "bottom_right": (2, 0),
            "top_right": (2, 1),
        }.items()
    }

    def add_edge(start, end):
        return topology.add_edge(
            vertices[start], vertices[end],
            Line(vertices[start].point, vertices[end].point),
        )

    left_edges = [
        add_edge("bottom_left", "bottom_shared"),
        add_edge("bottom_shared", "top_shared"),
        add_edge("top_shared", "top_left"),
        add_edge("top_left", "bottom_mid"),
        add_edge("bottom_mid", "bottom_left"),
    ]
    right_edges = [
        add_edge("bottom_shared", "bottom_right"),
        add_edge("bottom_right", "top_right"),
        add_edge("top_right", "top_shared"),
    ]
    left_loop = Loop()
    for edge in left_edges:
        left_loop.add_edge(edge.id)
    right_loop = Loop()
    for edge in right_edges:
        right_loop.add_edge(edge.id)
    right_loop.add_edge(left_edges[1].id, reversed=True)

    left_block = Block(
        doc.next_block_id(),
        left_loop.split_at_corners(
            topology,
            [
                vertices[name].id
                for name in ("bottom_left", "bottom_shared", "top_shared", "top_left")
            ],
        ),
    )
    right_block = Block(
        doc.next_block_id(),
        right_loop.split_at_corners(
            topology,
            [
                vertices[name].id
                for name in (
                    "bottom_shared", "bottom_right", "top_right", "top_shared"
                )
            ],
        ),
    )
    doc.add_block(left_block)
    doc.add_block(right_block)
    for edge in left_edges + right_edges:
        doc.mesh.set_spec(EdgeMeshSpec(edge.id, 5, UniformDistribution()))

    doc.set_edge_spec(EdgeMeshSpec(left_edges[1].id, 8, UniformDistribution()))

    assert left_block.sides[1].node_count == left_block.sides[3].node_count == 8
    assert left_block.sides[3].edge_ids() == [left_edges[3].id, left_edges[4].id]
    assert [
        doc.mesh.get_spec(edge_id).n_nodes
        for edge_id in left_block.sides[3].edge_ids()
    ] == [5, 4]
    assert right_block.sides[3].node_count == right_block.sides[1].node_count == 8
    meshes, errors = doc.generate_mesh()
    assert len(meshes) == 2
    assert errors == []


def test_set_edge_specs_preserves_explicit_values_and_is_atomic_on_conflict(qtbot):
    doc = Document()
    block = build_square_block(doc, n_nodes=5)
    first_edge_id = block.sides[0].edge_ids()[0]
    opposite_edge_id = block.sides[2].edge_ids()[0]
    original_specs = dict(doc.mesh.edge_specs)

    with pytest.raises(ValueError, match="conflict"):
        doc.set_edge_specs(
            [
                EdgeMeshSpec(first_edge_id, 8, UniformDistribution()),
                EdgeMeshSpec(opposite_edge_id, 5, UniformDistribution()),
            ]
        )

    assert doc.mesh.edge_specs == original_specs
    assert block.sides[0].node_count == block.sides[2].node_count == 5


def test_document_adds_point_sequence_as_single_spline_and_reuses_end_vertex(qtbot):
    doc = Document()
    existing_start = doc.topology.add_vertex(Point2D(5e-8, 0))
    points = [Point2D(0, 0), Point2D(1, 2), Point2D(3, 1)]

    edge = doc.add_point_sequence(points)

    assert len(doc.topology.edges()) == 1
    assert len(doc.topology.vertices()) == 2
    assert edge.start_vertex_id == existing_start.id
    assert isinstance(edge.geometry, Spline)
    assert edge.geometry.points == (existing_start.point, *points[1:])
    assert edge.geometry.get_grips() == [Point2D(1, 2)]
    restored = Document.from_dict(doc.to_dict())
    restored_edge = restored.topology.get_edge(edge.id)
    assert restored_edge.geometry == edge.geometry


def test_document_rejects_point_sequence_that_collapses_after_endpoint_snapping(qtbot):
    doc = Document()
    doc.topology.add_vertex(Point2D(0, 0))

    with pytest.raises(ValueError, match="Consecutive points must be distinct"):
        doc.add_point_sequence([Point2D(0, 0), Point2D(5e-8, 0)])

    assert len(doc.topology.vertices()) == 1
    assert doc.topology.edges() == []


def test_main_window_imports_point_sequence_from_file(qtbot, monkeypatch, tmp_path):
    from PyQt5.QtWidgets import QDialog

    from meshcad.gui.main_window import MainWindow

    path = tmp_path / "curve.csv"
    path.write_text("X,Y\n0,0\n1,2\n3,1\n", encoding="utf-8")
    window = MainWindow()
    qtbot.addWidget(window)

    monkeypatch.setattr(
        "meshcad.gui.main_window.QFileDialog.getOpenFileName",
        lambda *_args, **_kwargs: (str(path), ""),
    )

    class AcceptedPreview:
        def __init__(self, points, _parent):
            self.points = points

        def exec_(self):
            return QDialog.Accepted

    monkeypatch.setattr(
        "meshcad.gui.main_window.ImportPointSequenceDialog", AcceptedPreview
    )

    assert window.action_import_points.text() == "Import Point Sequence..."
    window._on_import_point_sequence()

    assert len(window.document.topology.edges()) == 1
    edge = window.document.topology.edges()[0]
    assert isinstance(edge.geometry, Spline)
    assert len(edge.geometry.points) == 3
    assert window.edges_panel.list_widget.count() == 1
    assert "Imported 3 points as edge 0." == window.status_label.text()


def test_main_window_cancelled_point_preview_does_not_import(qtbot, monkeypatch, tmp_path):
    from PyQt5.QtWidgets import QDialog

    from meshcad.gui.main_window import MainWindow

    path = tmp_path / "curve.csv"
    path.write_text("0,0\n1,2\n", encoding="utf-8")
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(
        "meshcad.gui.main_window.QFileDialog.getOpenFileName",
        lambda *_args, **_kwargs: (str(path), ""),
    )

    class CancelledPreview:
        def __init__(self, _points, _parent):
            pass

        def exec_(self):
            return QDialog.Rejected

    monkeypatch.setattr(
        "meshcad.gui.main_window.ImportPointSequenceDialog", CancelledPreview
    )

    window._on_import_point_sequence()

    assert window.document.topology.edges() == []
    assert window.document.topology.vertices() == []


def test_selecting_patch_highlights_its_edges_and_clears_previous_selection(qtbot):
    doc = Document()
    block = build_square_block(doc)
    edge_id = block.sides[0].edge_ids()[0]
    assigned_patch = doc.add_mesh_patch("wall")
    empty_patch = doc.add_mesh_patch("empty")
    doc.assign_mesh_patch_edges(assigned_patch.id, [edge_id])

    class Canvas:
        highlighted_edges = None

        def highlight_edges(self, edge_ids):
            self.highlighted_edges = edge_ids

    canvas = Canvas()
    edges_panel = EdgesPanel(doc, canvas)
    edges_panel.refresh()
    boundaries_panel = BoundariesPanel(doc, edges_panel)
    qtbot.addWidget(edges_panel)
    qtbot.addWidget(boundaries_panel)

    boundaries_panel.list_widget.setCurrentRow(0)
    assert edges_panel.selected_edge_ids() == [edge_id]
    assert canvas.highlighted_edges == [edge_id]

    boundaries_panel.list_widget.setCurrentRow(1)
    assert edges_panel.selected_edge_ids() == []
    assert canvas.highlighted_edges == []


def test_boundaries_panel_reports_invalid_edge_assignment(qtbot, monkeypatch):
    doc = Document()
    patch = doc.add_mesh_patch("wall")

    class SelectedEdges:
        def selected_edge_ids(self):
            return [42]

        def select_edges(self, _edge_ids):
            pass

    panel = BoundariesPanel(doc, SelectedEdges())
    qtbot.addWidget(panel)
    panel.list_widget.setCurrentRow(0)

    def reject_assignment(*_args):
        raise ValueError("Only exterior block edges can be assigned to mesh patches.")

    monkeypatch.setattr(
        doc,
        "assign_mesh_patch_edges",
        reject_assignment,
    )

    panel._assign()

    assert panel.status.text() == (
        "Only exterior block edges can be assigned to mesh patches."
    )
    assert doc.patches.get_patch(patch.id).edge_ids == ()


def test_document_loads_version_1_without_patches(qtbot):
    doc = Document()
    data = doc.to_dict()
    data["version"] = 1
    data.pop("patches")

    restored = Document.from_dict(data)

    assert restored.patches.patches() == ()


def test_document_load_from_replaces_patches(qtbot):
    target = Document()
    source = Document()
    source.patches.add_patch("wall")

    target.load_from(source)

    assert target.patches is source.patches


def test_patch_mutations_emit_signal(qtbot):
    doc = Document()
    with qtbot.waitSignal(doc.patches_changed, timeout=1000):
        patch = doc.add_mesh_patch("wall")
    block = build_square_block(doc)
    edge_ids = [
        edge_id for side in block.sides for edge_id in side.edge_ids()
    ]
    with qtbot.waitSignal(doc.patches_changed, timeout=1000):
        doc.assign_mesh_patch_edges(patch.id, edge_ids[:2])
    assert doc.patches.get_patch(patch.id).edge_ids == tuple(edge_ids[:2])
