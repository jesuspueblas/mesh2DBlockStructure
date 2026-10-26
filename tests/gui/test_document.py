import math

from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.distribution import UniformDistribution
from meshcad.core.mesh.model import EdgeMeshSpec
from meshcad.core.topology.block import Block
from meshcad.core.topology.loop import Loop
from meshcad.core.topology.topology import Topology
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

    # Desajuste lados 0/2 (inyectado directamente for saltar la propagacion)
    doc.mesh.set_spec(EdgeMeshSpec(e0.id, 4, UniformDistribution()))
    doc.mesh.set_spec(EdgeMeshSpec(e2.id, 6, UniformDistribution()))
    doc.mesh.set_spec(EdgeMeshSpec(e1.id, 4, UniformDistribution()))
    doc.mesh.set_spec(EdgeMeshSpec(e3.id, 4, UniformDistribution()))
    doc.recompute_blocks()

    meshes, errors = doc.generate_mesh()
    assert meshes == []
    assert len(errors) == 1
    assert "Bloque 0" in errors[0]


def test_document_boundary_model_round_trip_and_version_2(qtbot):
    doc = Document()
    patch = doc.boundaries.add_patch("inlet", "inlet")
    doc.boundaries.assign_edges(patch.id, [10, 11])

    data = doc.to_dict()
    restored = Document.from_dict(data)

    assert data["version"] == 2
    assert restored.boundaries.patches() == doc.boundaries.patches()


def test_document_loads_version_1_without_boundaries(qtbot):
    doc = Document()
    data = doc.to_dict()
    data["version"] = 1
    data.pop("boundaries")

    restored = Document.from_dict(data)

    assert restored.boundaries.patches() == ()


def test_document_load_from_replaces_boundaries(qtbot):
    target = Document()
    source = Document()
    source.boundaries.add_patch("wall", "wall")

    target.load_from(source)

    assert target.boundaries is source.boundaries


def test_boundary_mutations_emit_signal(qtbot):
    doc = Document()
    with qtbot.waitSignal(doc.boundaries_changed, timeout=1000):
        patch = doc.add_boundary_patch("wall", "wall")
    with qtbot.waitSignal(doc.boundaries_changed, timeout=1000):
        doc.assign_boundary_edges(patch.id, [1, 2])
    assert doc.boundaries.get_patch(patch.id).edge_ids == (1, 2)
