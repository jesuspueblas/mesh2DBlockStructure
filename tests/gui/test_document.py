import math

import pytest

from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.distribution import UniformDistribution
from meshcad.core.mesh.model import EdgeMeshSpec
from meshcad.core.topology.block import Block
from meshcad.core.topology.loop import Loop
from meshcad.core.topology.topology import Topology
from meshcad.gui.boundaries_panel import BoundariesPanel
from meshcad.gui.document import Document


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


def test_boundaries_panel_reports_invalid_edge_assignment(qtbot, monkeypatch):
    doc = Document()
    patch = doc.add_mesh_patch("wall")

    class SelectedEdges:
        def selected_edge_ids(self):
            return [42]

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
