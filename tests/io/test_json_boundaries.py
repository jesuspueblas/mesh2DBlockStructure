from meshcad.core.boundary import BoundaryModel, BoundaryType
from meshcad.io.json_io import boundary_model_from_dict, boundary_model_to_dict


def test_boundary_model_round_trip():
    model = BoundaryModel()
    inlet = model.add_patch("inlet", BoundaryType.INLET)
    model.assign_edges(inlet.id, [8, 3])
    model.add_patch("outlet", BoundaryType.OUTLET)

    data = boundary_model_to_dict(model)
    restored = boundary_model_from_dict(data)

    assert restored.patches() == model.patches()
    assert restored.next_patch_id == model.next_patch_id


def test_missing_boundary_section_loads_as_empty_model():
    restored = boundary_model_from_dict({})
    assert restored.patches() == ()
    assert restored.next_patch_id == 0
