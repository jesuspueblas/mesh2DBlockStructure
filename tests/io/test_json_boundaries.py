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


def test_periodic_pairs_round_trip():
    from meshcad.core.boundary import PeriodicTransform
    model = BoundaryModel()
    a = model.add_patch("a", "periodic")
    b = model.add_patch("b", "periodic")
    model.add_periodic_pair("pair", a.id, b.id, True, 1e-7,
                            PeriodicTransform(2.0, -3.0))
    restored = boundary_model_from_dict(boundary_model_to_dict(model))
    assert restored.periodic_pairs() == model.periodic_pairs()
    assert restored.next_periodic_pair_id == model.next_periodic_pair_id
