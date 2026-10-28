from meshcad.core.boundary import MeshPatch, PatchModel

def test_patch_has_only_geometric_information():
    patch=MeshPatch(2,"outer",(4,3,4))
    assert patch.id==2 and patch.name=="outer" and patch.edge_ids==(3,4)
    assert not hasattr(patch,"boundary_type")

def test_edge_assignment_is_unique():
    model=PatchModel(); a=model.add_patch("a"); b=model.add_patch("b")
    model.assign_edges(a.id,[1,2]); model.assign_edges(b.id,[2,3])
    assert model.get_patch(a.id).edge_ids==(1,)
    assert model.get_patch(b.id).edge_ids==(2,3)
