from dataclasses import FrozenInstanceError

import pytest

from meshcad.core.boundary import (
    BoundaryIssueCode,
    BoundaryModel,
    BoundaryPatch,
    BoundaryType,
)
from meshcad.core.topology.block import Block
from meshcad.core.topology.block_side import BlockSide
from meshcad.core.topology.edge import OrientedEdge


def _side(*edge_ids):
    return BlockSide(tuple(OrientedEdge(edge_id) for edge_id in edge_ids))


def _block(block_id, *sides):
    return Block(block_id, tuple(sides))


def test_add_rename_change_type_and_remove_patch():
    model = BoundaryModel()
    patch = model.add_patch(" inlet ", BoundaryType.INLET)
    assert patch == BoundaryPatch(0, "inlet", BoundaryType.INLET)
    assert model.next_patch_id == 1
    assert model.rename_patch(0, "main_inlet").name == "main_inlet"
    assert model.set_patch_type(0, "outlet").boundary_type is BoundaryType.OUTLET
    assert model.remove_patch(0).id == 0
    assert model.patches() == ()


def test_names_are_non_empty_unique_and_case_insensitive():
    model = BoundaryModel()
    model.add_patch("Wall", "wall")
    with pytest.raises(ValueError, match="already exists"):
        model.add_patch(" wall ", "inlet")
    with pytest.raises(ValueError, match="must not be empty"):
        model.add_patch("  ", "wall")


def test_assigning_an_edge_moves_it_from_the_previous_patch():
    model = BoundaryModel()
    first = model.add_patch("first", "wall")
    second = model.add_patch("second", "outlet")
    model.assign_edges(first.id, [3, 2, 3])
    model.assign_edges(second.id, [3, 4])
    assert model.get_patch(first.id).edge_ids == (2,)
    assert model.get_patch(second.id).edge_ids == (3, 4)
    assert model.patch_for_edge(3).id == second.id


def test_unassign_and_discard_edges_are_idempotent():
    model = BoundaryModel()
    patch = model.add_patch("wall", "wall")
    model.assign_edges(patch.id, [1, 2, 3])
    assert model.unassign_edges(patch.id, [2, 99]).edge_ids == (1, 3)
    model.discard_edges([1, 99])
    model.discard_edges([1])
    assert model.get_patch(patch.id).edge_ids == (3,)


def test_restore_preserves_ids_counter_and_rejects_duplicate_assignments():
    patches = (
        BoundaryPatch(3, "inlet", BoundaryType.INLET, (4,)),
        BoundaryPatch(7, "wall", BoundaryType.WALL, (5,)),
    )
    model = BoundaryModel.restore(patches, next_patch_id=10)
    assert [patch.id for patch in model.patches()] == [3, 7]
    assert model.next_patch_id == 10
    with pytest.raises(ValueError, match="more than one"):
        BoundaryModel.restore((patches[0], BoundaryPatch(9, "x", BoundaryType.WALL, (4,))))


def test_validation_reports_empty_unknown_internal_and_unassigned_edges():
    left = _block(0, _side(10), _side(99), _side(12), _side(13))
    right = _block(1, _side(20), _side(21), _side(22), _side(99))
    model = BoundaryModel()
    wall = model.add_patch("wall", "wall")
    empty = model.add_patch("empty", "outlet")
    model.assign_edges(wall.id, [10, 99, 1234])

    result = model.validate([left, right])
    codes = [issue.code for issue in result.issues]
    assert result.is_valid is False
    assert BoundaryIssueCode.EMPTY_PATCH in codes
    assert BoundaryIssueCode.UNKNOWN_EDGE in codes
    assert BoundaryIssueCode.INTERNAL_EDGE in codes
    assert codes.count(BoundaryIssueCode.UNASSIGNED_EXTERNAL_EDGE) == 5
    assert empty.edge_ids == ()


def test_fully_assigned_single_block_is_valid():
    block = _block(0, _side(1), _side(2), _side(3), _side(4))
    model = BoundaryModel()
    wall = model.add_patch("walls", "wall")
    model.assign_edges(wall.id, [1, 2, 3, 4])
    assert model.validate([block]).is_valid is True


def test_patch_is_immutable():
    patch = BoundaryPatch(0, "wall", BoundaryType.WALL)
    with pytest.raises(FrozenInstanceError):
        patch.name = "changed"
