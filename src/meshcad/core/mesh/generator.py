"""Block-structured mesh generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.model import MeshModel
from meshcad.core.mesh.tfi import tfi_grid
from meshcad.core.mesh.smoothing import SmoothingOptions, improve_grid
from meshcad.core.topology.block import Block
from meshcad.core.topology.topology import Topology


@dataclass
class BlockMesh:
    """Structured mesh for a block.

    grid[j][i] with j in [0, n_v) and i in [0, n_u).
    n_u is the number of nodes on sides 0 and 2.
    n_v is the number of nodes on sides 1 and 3.
    """

    block_id: int
    grid: List[List[Point2D]]

    @property
    def n_u(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    @property
    def n_v(self) -> int:
        return len(self.grid)

    def cell_count(self) -> int:
        if self.n_u < 2 or self.n_v < 2:
            return 0
        return (self.n_u - 1) * (self.n_v - 1)

    def point(self, i: int, j: int) -> Point2D:
        return self.grid[j][i]


def mesh_block(block: Block, topology: Topology, mesh_model: MeshModel, options: Optional[SmoothingOptions] = None) -> BlockMesh:
    """Generate a block mesh from its four sides and the mesh model."""
    side_samples = [
        mesh_model.side_samples(side, topology) for side in block.sides
    ]
    s0, s1, s2, s3 = side_samples

    if len(s0) < 2 or len(s1) < 2 or len(s2) < 2 or len(s3) < 2:
        raise ValueError("Each side must have at least two nodes")

    if len(s0) != len(s2):
        raise ValueError(
            "Sides 0 and 2 have different node counts: {} vs {}".format(
                len(s0), len(s2)
            )
        )
    if len(s1) != len(s3):
        raise ValueError(
            "Sides 1 and 3 have different node counts: {} vs {}".format(
                len(s1), len(s3)
            )
        )

    grid = tfi_grid(s0, s1, s2, s3)
    if options is not None:
        grid = improve_grid(grid, options)
    return BlockMesh(block_id=block.id, grid=grid)
