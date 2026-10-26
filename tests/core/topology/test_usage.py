from dataclasses import FrozenInstanceError

import pytest

from meshcad.core.topology.block import Block
from meshcad.core.topology.block_side import BlockSide
from meshcad.core.topology.edge import OrientedEdge
from meshcad.core.topology.usage import (
    EdgeUse,
    external_edge_ids,
    find_edge_uses,
    internal_edge_ids,
    non_manifold_edge_ids,
)


def _side(*edges):
    return BlockSide(tuple(OrientedEdge(edge_id, reversed_) for edge_id, reversed_ in edges))


def _block(block_id, side_0, side_1, side_2, side_3):
    return Block(block_id, (side_0, side_1, side_2, side_3))


def test_empty_blocks_have_no_edge_uses():
    assert find_edge_uses([]) == {}
    assert external_edge_ids([]) == ()
    assert internal_edge_ids([]) == ()
    assert non_manifold_edge_ids([]) == ()


def test_single_block_edges_are_external():
    block = _block(7, _side((10, False)), _side((11, False)),
                   _side((12, False)), _side((13, False)))

    assert external_edge_ids([block]) == (10, 11, 12, 13)
    assert internal_edge_ids([block]) == ()
    assert non_manifold_edge_ids([block]) == ()


def test_shared_edge_is_internal_and_keeps_opposite_orientations():
    left = _block(20, _side((0, False)), _side((9, False)),
                  _side((2, False)), _side((3, False)))
    right = _block(5, _side((4, False)), _side((5, False)),
                   _side((6, False)), _side((9, True)))

    usage = find_edge_uses([left, right])

    assert internal_edge_ids([left, right]) == (9,)
    assert usage[9] == (
        EdgeUse(9, 5, 3, 0, True),
        EdgeUse(9, 20, 1, 0, False),
    )


def test_compound_side_records_edge_positions():
    block = _block(
        3,
        _side((40, False), (41, True), (42, False)),
        _side((50, False)),
        _side((60, False)),
        _side((70, False)),
    )

    usage = find_edge_uses([block])

    assert usage[40][0].edge_index == 0
    assert usage[41][0] == EdgeUse(41, 3, 0, 1, True)
    assert usage[42][0].edge_index == 2


def test_edge_used_by_three_blocks_is_non_manifold():
    blocks = [
        _block(block_id, _side((99, reversed_)), _side(), _side(), _side())
        for block_id, reversed_ in ((8, False), (2, True), (15, False))
    ]

    assert non_manifold_edge_ids(blocks) == (99,)
    assert external_edge_ids(blocks) == ()
    assert internal_edge_ids(blocks) == ()


def test_result_is_independent_of_block_input_order():
    first = _block(12, _side((5, False)), _side(), _side(), _side())
    second = _block(1, _side(), _side((5, True)), _side(), _side())

    assert find_edge_uses([first, second]) == find_edge_uses([second, first])


def test_repeated_use_inside_one_block_is_not_hidden():
    block = _block(4, _side((7, False)), _side((7, True)), _side(), _side())

    assert len(find_edge_uses([block])[7]) == 2
    assert internal_edge_ids([block]) == (7,)


def test_edge_use_is_immutable():
    use = EdgeUse(1, 2, 3, 4, False)

    with pytest.raises(FrozenInstanceError):
        use.edge_id = 99
