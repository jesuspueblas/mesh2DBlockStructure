"""Queries for how CAD edges are used by structured blocks.

This module is deliberately independent of geometry, meshing, Qt, and I/O.  It
provides the topological information required by boundary-condition handling
and by the future finite-volume connectivity builder.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, Dict, Iterable, Tuple

from meshcad.core.topology.block import Block


@dataclass(frozen=True, order=True)
class EdgeUse:
    """One occurrence of an oriented edge in a logical block side.

    ``side_index`` is the logical side position in ``Block.sides`` and
    ``edge_index`` is the position inside a possibly compound ``BlockSide``.
    """

    edge_id: int
    block_id: int
    side_index: int
    edge_index: int
    reversed: bool


EdgeUsageMap = Dict[int, Tuple[EdgeUse, ...]]


def find_edge_uses(blocks: Iterable[Block]) -> EdgeUsageMap:
    """Return every block occurrence grouped by edge identifier.

    The result is deterministic: edge identifiers are sorted and the uses of
    each edge are sorted by block, side, and position.  All occurrences are
    retained, including accidental repeated uses inside one block, because
    those repetitions must remain visible to validation code.
    """

    grouped: DefaultDict[int, list[EdgeUse]] = defaultdict(list)
    for block in blocks:
        for side_index, side in enumerate(block.sides):
            for edge_index, oriented_edge in enumerate(side.oriented_edges):
                grouped[oriented_edge.edge_id].append(
                    EdgeUse(
                        edge_id=oriented_edge.edge_id,
                        block_id=block.id,
                        side_index=side_index,
                        edge_index=edge_index,
                        reversed=oriented_edge.reversed,
                    )
                )

    return {
        edge_id: tuple(sorted(uses))
        for edge_id, uses in sorted(grouped.items())
    }


def _edge_ids_with_use_count(blocks: Iterable[Block], count: int) -> Tuple[int, ...]:
    usage = find_edge_uses(blocks)
    return tuple(edge_id for edge_id, uses in usage.items() if len(uses) == count)


def external_edge_ids(blocks: Iterable[Block]) -> Tuple[int, ...]:
    """Return edges used exactly once, i.e. candidate exterior boundaries."""

    return _edge_ids_with_use_count(blocks, 1)


def internal_edge_ids(blocks: Iterable[Block]) -> Tuple[int, ...]:
    """Return edges used exactly twice, i.e. candidate block interfaces."""

    return _edge_ids_with_use_count(blocks, 2)


def non_manifold_edge_ids(blocks: Iterable[Block]) -> Tuple[int, ...]:
    """Return edges used more than twice by the supplied blocks."""

    usage = find_edge_uses(blocks)
    return tuple(edge_id for edge_id, uses in usage.items() if len(uses) > 2)
