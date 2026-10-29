import pytest

from meshcad.core.boundary import PatchModel
from meshcad.core.cfd import ConnectivityError, build_cfd_mesh
from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.distribution import UniformDistribution
from meshcad.core.mesh.generator import mesh_block
from meshcad.core.mesh.model import EdgeMeshSpec, MeshModel
from meshcad.core.topology.block import Block
from meshcad.core.topology.loop import Loop
from meshcad.core.topology.topology import Topology
from meshcad.io.cfd_mesh_io import cfd_mesh_to_dict


def _single_square(n=3):
    topology = Topology()
    vertices = [topology.add_vertex(Point2D(*p)) for p in ((0, 0), (1, 0), (1, 1), (0, 1))]
    edges = []
    for first, second in zip(vertices, vertices[1:] + vertices[:1]):
        edges.append(topology.add_edge(first, second, Line(first.point, second.point)))
    loop = Loop()
    for edge in edges:
        loop.add_edge(edge.id)
    block = Block(0, loop.split_at_corners(topology, [vertex.id for vertex in vertices]))
    model = MeshModel()
    for edge in edges:
        model.set_spec(EdgeMeshSpec(edge.id, n, UniformDistribution()))
    boundaries = PatchModel()
    wall = boundaries.add_patch("wall")
    boundaries.assign_edges(wall.id, [edge.id for edge in edges])
    return topology, [block], model, boundaries


def test_single_block_counts_and_owner_neighbour():
    topology, blocks, model, boundaries = _single_square(3)
    meshes = [mesh_block(blocks[0], topology, model)]
    cfd = build_cfd_mesh(meshes, blocks, topology, model, boundaries)
    assert len(cfd.nodes) == 9
    assert len(cfd.cells) == 4
    assert len(cfd.faces) == 12
    assert len(cfd.internal_faces) == 4
    assert len(cfd.boundary_faces) == 8
    assert all(face.neighbour is not None for face in cfd.internal_faces)
    assert all(face.patch_id == 0 for face in cfd.boundary_faces)
    assert all(cell.area > 0.0 for cell in cfd.cells)


def test_two_blocks_merge_interface_nodes_and_faces():
    topology = Topology()
    v0, v1, v2, v3, v4, v5 = [
        topology.add_vertex(Point2D(*point))
        for point in ((0, 0), (1, 0), (1, 1), (0, 1), (2, 0), (2, 1))
    ]
    e0 = topology.add_edge(v0, v1, Line(v0.point, v1.point))
    shared = topology.add_edge(v1, v2, Line(v1.point, v2.point))
    e2 = topology.add_edge(v2, v3, Line(v2.point, v3.point))
    e3 = topology.add_edge(v3, v0, Line(v3.point, v0.point))
    e4 = topology.add_edge(v1, v4, Line(v1.point, v4.point))
    e5 = topology.add_edge(v4, v5, Line(v4.point, v5.point))
    e6 = topology.add_edge(v5, v2, Line(v5.point, v2.point))
    left = Loop()
    for edge in (e0, shared, e2, e3):
        left.add_edge(edge.id)
    right = Loop()
    for edge in (e4, e5, e6):
        right.add_edge(edge.id)
    right.add_edge(shared.id, reversed=True)
    blocks = [
        Block(0, left.split_at_corners(topology, [v0.id, v1.id, v2.id, v3.id])),
        Block(1, right.split_at_corners(topology, [v1.id, v4.id, v5.id, v2.id])),
    ]
    model = MeshModel()
    for edge in topology.edges():
        model.set_spec(EdgeMeshSpec(edge.id, 3, UniformDistribution()))
    boundaries = PatchModel()
    wall = boundaries.add_patch("wall")
    boundaries.assign_edges(wall.id, [e0.id, e2.id, e3.id, e4.id, e5.id, e6.id])
    meshes = [mesh_block(block, topology, model) for block in blocks]
    cfd = build_cfd_mesh(meshes, blocks, topology, model, boundaries)
    assert len(cfd.nodes) == 15
    assert len(cfd.cells) == 8
    assert len(cfd.internal_faces) == 10
    assert len(cfd.boundary_faces) == 12
    interface_faces = [
        face for face in cfd.internal_faces
        if all(cfd.nodes[node_id].x == 1 for node_id in face.node_ids)
    ]
    assert len(interface_faces) == 2
    assert all(face.patch_id is None for face in interface_faces)
    assert all(face.cad_edge_id is None for face in interface_faces)
    exported = cfd_mesh_to_dict(cfd, boundaries)
    assert all(exported["faces"]["patch"][face.id] == -1 for face in interface_faces)
    assert all(
        exported["faces"]["neighbour"][face.id] != -1 for face in interface_faces
    )
    assert all(
        face.id not in exported["patches"][0]["faces"] for face in interface_faces
    )


def test_internal_block_interface_cannot_be_assigned_to_patch():
    topology = Topology()
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
    blocks = [
        Block(
            0,
            left_loop.split_at_corners(topology, [v.id for v in (v0, v1, v2, v3)]),
        ),
        Block(
            1,
            right_loop.split_at_corners(topology, [v.id for v in (v1, v4, v5, v2)]),
        ),
    ]
    model = MeshModel()
    for edge in edges:
        model.set_spec(EdgeMeshSpec(edge.id, 3, UniformDistribution()))
    patches = PatchModel()
    wall = patches.add_patch("wall")
    patches.assign_edges(
        wall.id, [edge.id for edge in edges if edge.id != edges[1].id]
    )
    patches.assign_edges(wall.id, [edges[1].id])
    meshes = [mesh_block(block, topology, model) for block in blocks]

    with pytest.raises(ConnectivityError, match="not exterior"):
        build_cfd_mesh(meshes, blocks, topology, model, patches)
