import math

import pytest

from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.distribution import UniformDistribution
from meshcad.core.mesh.generator import BlockMesh, mesh_block
from meshcad.core.mesh.model import EdgeMeshSpec, MeshModel
from meshcad.core.topology.block import Block
from meshcad.core.topology.loop import Loop
from meshcad.core.topology.topology import Topology


def build_square_block(n_nodes=4):
    """Square [0, 1] x [0, 1] with four edges and one block."""
    t = Topology()
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
    block = Block(0, sides)

    model = MeshModel()
    for e in (e0, e1, e2, e3):
        model.set_spec(EdgeMeshSpec(e.id, n_nodes, UniformDistribution()))
    return t, block, model, (v0, v1, v2, v3), (e0, e1, e2, e3)


def test_mesh_block_grid_size():
    t, block, model, _, _ = build_square_block(n_nodes=4)
    bm = mesh_block(block, t, model)
    assert bm.n_u == 4
    assert bm.n_v == 4
    assert bm.cell_count() == 9


def test_mesh_block_corners():
    t, block, model, (v0, v1, v2, v3), _ = build_square_block(n_nodes=4)
    bm = mesh_block(block, t, model)
    assert bm.point(0, 0) == Point2D(0, 0)
    assert bm.point(3, 0) == Point2D(1, 0)
    assert bm.point(3, 3) == Point2D(1, 1)
    assert bm.point(0, 3) == Point2D(0, 1)


def test_mesh_block_rectangle_uniform():
    t, block, model, _, _ = build_square_block(n_nodes=5)
    bm = mesh_block(block, t, model)
    for j in range(5):
        for i in range(5):
            assert math.isclose(bm.point(i, j).x, i / 4.0)
            assert math.isclose(bm.point(i, j).y, j / 4.0)


def test_mesh_block_requires_matching_opposite_sides():
    t, block, model, _, (e0, e1, e2, e3) = build_square_block(n_nodes=4)
    model.set_spec(EdgeMeshSpec(e0.id, 4, UniformDistribution()))
    model.set_spec(EdgeMeshSpec(e2.id, 6, UniformDistribution()))  # Mismatch.
    with pytest.raises(ValueError):
        mesh_block(block, t, model)


def test_mesh_block_with_different_counts_per_direction():
    t, block, model, _, (e0, e1, e2, e3) = build_square_block(n_nodes=4)
    model.set_spec(EdgeMeshSpec(e0.id, 5, UniformDistribution()))
    model.set_spec(EdgeMeshSpec(e2.id, 5, UniformDistribution()))
    model.set_spec(EdgeMeshSpec(e1.id, 7, UniformDistribution()))
    model.set_spec(EdgeMeshSpec(e3.id, 7, UniformDistribution()))
    bm = mesh_block(block, t, model)
    assert bm.n_u == 5
    assert bm.n_v == 7


def test_adjacent_blocks_are_conformal():
    """Two squares sharing an edge must produce the same line of nodes."""
    t = Topology()
    # Left square.
    v0 = t.add_vertex(Point2D(0, 0))
    v1 = t.add_vertex(Point2D(1, 0))
    v2 = t.add_vertex(Point2D(1, 1))
    v3 = t.add_vertex(Point2D(0, 1))
    # Right square.
    v4 = t.add_vertex(Point2D(2, 0))
    v5 = t.add_vertex(Point2D(2, 1))

    e_bottom_left = t.add_edge(v0, v1, Line(v0.point, v1.point))
    e_shared = t.add_edge(v1, v2, Line(v1.point, v2.point))       # shared
    e_top_left = t.add_edge(v2, v3, Line(v2.point, v3.point))
    e_left = t.add_edge(v3, v0, Line(v3.point, v0.point))
    e_bottom_right = t.add_edge(v1, v4, Line(v1.point, v4.point))
    e_top_right = t.add_edge(v4, v5, Line(v4.point, v5.point))
    e_right = t.add_edge(v2, v5, Line(v2.point, v5.point))

    loop_left = Loop()
    loop_left.add_edge(e_bottom_left.id)
    loop_left.add_edge(e_shared.id)
    loop_left.add_edge(e_top_left.id)
    loop_left.add_edge(e_left.id)

    loop_right = Loop()
    loop_right.add_edge(e_bottom_right.id)
    loop_right.add_edge(e_top_right.id)
    loop_right.add_edge(e_right.id, reversed=True)
    loop_right.add_edge(e_shared.id, reversed=True)

    sides_left = loop_left.split_at_corners(t, [v0.id, v1.id, v2.id, v3.id])
    sides_right = loop_right.split_at_corners(t, [v1.id, v4.id, v5.id, v2.id])
    block_left = Block(0, sides_left)
    block_right = Block(1, sides_right)

    model = MeshModel()
    n_nodes = 5
    for e in (e_bottom_left, e_shared, e_top_left, e_left,
              e_bottom_right, e_top_right, e_right):
        model.set_spec(EdgeMeshSpec(e.id, n_nodes, UniformDistribution()))

    bm_left = mesh_block(block_left, t, model)
    bm_right = mesh_block(block_right, t, model)

    # The left block's east side is column n_u-1.
    left_edge_points = [
        (round(bm_left.point(bm_left.n_u - 1, j).x, 9),
         round(bm_left.point(bm_left.n_u - 1, j).y, 9))
        for j in range(bm_left.n_v)
    ]
    # The right block's west side is column 0.
    right_edge_points = [
        (round(bm_right.point(0, j).x, 9),
         round(bm_right.point(0, j).y, 9))
        for j in range(bm_right.n_v)
    ]

    # The point sets must match, even if their order is reversed.
    assert set(left_edge_points) == set(right_edge_points)
