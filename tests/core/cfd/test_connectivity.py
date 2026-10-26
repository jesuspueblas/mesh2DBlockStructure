from meshcad.core.boundary import BoundaryModel
from meshcad.core.cfd import build_cfd_mesh
from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.distribution import UniformDistribution
from meshcad.core.mesh.generator import mesh_block
from meshcad.core.mesh.model import EdgeMeshSpec, MeshModel
from meshcad.core.topology.block import Block
from meshcad.core.topology.loop import Loop
from meshcad.core.topology.topology import Topology


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
    boundaries = BoundaryModel()
    wall = boundaries.add_patch("wall", "wall")
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
    boundaries = BoundaryModel()
    wall = boundaries.add_patch("wall", "wall")
    boundaries.assign_edges(wall.id, [e0.id, e2.id, e3.id, e4.id, e5.id, e6.id])
    meshes = [mesh_block(block, topology, model) for block in blocks]
    cfd = build_cfd_mesh(meshes, blocks, topology, model, boundaries)
    assert len(cfd.nodes) == 15
    assert len(cfd.cells) == 8
    assert len(cfd.internal_faces) == 10
    assert len(cfd.boundary_faces) == 12
    assert sum(1 for face in cfd.internal_faces if all(cfd.nodes[n].x == 1 for n in face.node_ids)) == 2
