import pytest

from meshcad.core.boundary import MeshPatch, PatchModel

def test_patch_has_only_geometric_information():
    patch=MeshPatch(2,"outer",(4,3))
    assert patch.id==2 and patch.name=="outer" and patch.edge_ids==(3,4)
    assert not hasattr(patch,"boundary_type")

def test_patch_rejects_duplicate_edges():
    with pytest.raises(ValueError, match="cannot contain duplicate edge IDs"):
        MeshPatch(2,"outer",(3,4,3))

def test_edge_assignment_rejects_duplicates_without_mutating_model():
    model=PatchModel(); a=model.add_patch("a"); b=model.add_patch("b")
    model.assign_edges(a.id,[1,2])

    with pytest.raises(ValueError, match="more than once"):
        model.assign_edges(a.id,[3,3])
    with pytest.raises(ValueError, match="already assigned to patch 'a'"):
        model.assign_edges(a.id,[2])
    with pytest.raises(ValueError, match="already assigned to patch 'a'"):
        model.assign_edges(b.id,[2,3])

    assert model.get_patch(a.id).edge_ids==(1,2)
    assert model.get_patch(b.id).edge_ids==()

def test_restore_rejects_edges_shared_between_patches():
    with pytest.raises(ValueError, match="assigned to more than one mesh patch"):
        PatchModel.restore((MeshPatch(1,"a",(1,2)), MeshPatch(2,"b",(2,3))))
