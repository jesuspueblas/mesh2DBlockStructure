"""Structured block side: sequence of oriented edges."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from meshcad.core.topology.edge import OrientedEdge


@dataclass
class BlockSide:
    """One side of a structured block.

    A side is a sequence of OrientedEdge objects traversed from start to
    end. Multiple edges can form one side.

    node_count is the number of mesh nodes along this side. It remains 0
    until distributions are assigned.
    """

    oriented_edges: Tuple[OrientedEdge, ...]
    node_count: int = 0

    def __len__(self) -> int:
        return len(self.oriented_edges)

    def edge_ids(self) -> List[int]:
        return [oe.edge_id for oe in self.oriented_edges]

    def __repr__(self) -> str:
        return "BlockSide(edges={}, node_count={})".format(
            self.edge_ids(), self.node_count
        )
