"""Mesh model: per-edge distributions and side queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.distribution import (
    NodeDistribution,
    UniformDistribution,
)
from meshcad.core.topology.block_side import BlockSide
from meshcad.core.topology.topology import Topology

DEFAULT_N_NODES = 5


@dataclass
class EdgeMeshSpec:
    """Mesh specification for an edge.

    n_nodes is the total number of nodes, including both endpoints.
    distribution defines their positions along parameter t in [0, 1].
    """

    edge_id: int
    n_nodes: int
    distribution: NodeDistribution

    def __post_init__(self):
        if self.n_nodes < 2:
            raise ValueError("n_nodes must be >= 2")


class MeshModel:
    """Node distributions associated with edges.

    The same edge can belong to multiple blocks; its distribution is stored
    once and shared by all of them.
    """

    def __init__(self) -> None:
        self.edge_specs: Dict[int, EdgeMeshSpec] = {}

    # ----------------------------- access -------------------------------- #

    def get_spec(self, edge_id: int) -> EdgeMeshSpec:
        spec = self.edge_specs.get(edge_id)
        if spec is None:
            return EdgeMeshSpec(edge_id, DEFAULT_N_NODES, UniformDistribution())
        return spec

    def set_spec(self, spec: EdgeMeshSpec) -> None:
        self.edge_specs[spec.edge_id] = spec

    def clear_spec(self, edge_id: int) -> None:
        self.edge_specs.pop(edge_id, None)

    # ----------------------------- queries ------------------------------ #

    def side_node_count(self, side: BlockSide) -> int:
        """Return the number of nodes on a side by concatenating its edges.

        If the side has k edges with n_0, ..., n_{k-1} nodes each, the total
        is sum(n_i) - (k - 1), because consecutive edges share an endpoint.
        """
        if not side.oriented_edges:
            return 0
        total = 0
        for i, oe in enumerate(side.oriented_edges):
            spec = self.get_spec(oe.edge_id)
            total += spec.n_nodes if i == 0 else spec.n_nodes - 1
        return total

    def side_samples(self, side: BlockSide, topology: Topology) -> List[Point2D]:
        """Points along a side in traversal order."""
        samples: List[Point2D] = []
        for i, oe in enumerate(side.oriented_edges):
            edge = topology.get_edge(oe.edge_id)
            spec = self.get_spec(oe.edge_id)
            pts = spec.distribution.sample(edge.geometry, spec.n_nodes)
            if oe.reversed:
                pts = list(reversed(pts))
            if i > 0:
                pts = pts[1:]
            samples.extend(pts)
        return samples
