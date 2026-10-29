"""Four-sided structured block."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from meshcad.core.topology.block_side import BlockSide


@dataclass
class Block:
    """Four-sided structured block.

    Side numbering convention:
        side 0 <-> side 2 are opposite
        side 1 <-> side 3 are opposite

    Opposite sides must have the same number of nodes. Until distributions
    are assigned, node_count is 0 for every side, so validation passes
    trivially.
    """

    id: int
    sides: Tuple[BlockSide, BlockSide, BlockSide, BlockSide]

    def validate_opposite_sides(self) -> None:
        s0, s1, s2, s3 = self.sides
        if s0.node_count != s2.node_count:
            raise ValueError(
                "Opposite sides 0 and 2 must have the same number "
                "of nodes: {} vs {}".format(s0.node_count, s2.node_count)
            )
        if s1.node_count != s3.node_count:
            raise ValueError(
                "Opposite sides 1 and 3 must have the same number "
                "of nodes: {} vs {}".format(s1.node_count, s3.node_count)
            )

    def __repr__(self) -> str:
        return "Block(id={}, sides=[{}])".format(
            self.id, ", ".join(repr(s) for s in self.sides)
        )
