import json

import pytest

from meshcad.core.boundary import BoundaryModel
from meshcad.core.cfd import CfdCell, CfdFace, CfdMesh, PeriodicFaceLink
from meshcad.core.geometry.point import Point2D
from meshcad.io.cfd_mesh_io import (
    CfdMeshExportError,
    cfd_mesh_to_dict,
    write_cfd_mesh_json,
)


def _square_mesh(patch_id=0):
    nodes = tuple(Point2D(*point) for point in ((0, 0), (1, 0), (1, 1), (0, 1)))
    cells = (CfdCell(0, (0, 1, 2, 3), 0, 0, 0, 1.0),)
    faces = tuple(
        CfdFace(index, edge, 0, patch_id=patch_id)
        for index, edge in enumerate(((0, 1), (1, 2), (2, 3), (3, 0)))
    )
    return CfdMesh(nodes, cells, faces)


def _wall_boundaries():
    boundaries = BoundaryModel()
    boundaries.add_patch("walls", "wall")
    return boundaries


def test_compact_data_contains_nodes_faces_cells_and_patches():
    data = cfd_mesh_to_dict(_square_mesh(), _wall_boundaries())
    assert data["format"] == "meshcad-cfd-mesh"
    assert data["version"] == 1
    assert data["nodes"]["coordinates"] == [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    assert data["faces"]["nodes"] == [[0, 1], [1, 2], [2, 3], [3, 0]]
    assert data["faces"]["owner"] == [0, 0, 0, 0]
    assert data["faces"]["neighbour"] == [-1, -1, -1, -1]
    assert data["cells"] == {"faces": [[0, 1, 2, 3]], "face_signs": [[1, 1, 1, 1]]}
    assert data["patches"] == [{"id": 0, "name": "walls", "type": "wall", "faces": [0, 1, 2, 3]}]


def test_internal_face_is_shared_with_opposite_signs():
    nodes = tuple(Point2D(*point) for point in ((0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)))
    cells = (CfdCell(0, (0, 1, 4, 3), 0, 0, 0, 1), CfdCell(1, (1, 2, 5, 4), 0, 1, 0, 1))
    faces = (
        CfdFace(0, (0, 1), 0, patch_id=0), CfdFace(1, (1, 4), 0, 1),
        CfdFace(2, (4, 3), 0, patch_id=0), CfdFace(3, (3, 0), 0, patch_id=0),
        CfdFace(4, (1, 2), 1, patch_id=0), CfdFace(5, (2, 5), 1, patch_id=0),
        CfdFace(6, (5, 4), 1, patch_id=0),
    )
    data = cfd_mesh_to_dict(CfdMesh(nodes, cells, faces), _wall_boundaries())
    assert data["faces"]["neighbour"][1] == 1
    left_index = data["cells"]["faces"][0].index(1)
    right_index = data["cells"]["faces"][1].index(1)
    assert data["cells"]["face_signs"][0][left_index] == 1
    assert data["cells"]["face_signs"][1][right_index] == -1
    assert 1 not in data["patches"][0]["faces"]


def test_writer_is_compact_by_default_and_pretty_on_request(tmp_path):
    compact = tmp_path / "mesh.json"
    pretty = tmp_path / "mesh-pretty.json"
    mesh, boundaries = _square_mesh(), _wall_boundaries()
    write_cfd_mesh_json(compact, mesh, boundaries)
    write_cfd_mesh_json(pretty, mesh, boundaries, pretty=True)
    compact_text = compact.read_text(encoding="utf-8")
    pretty_text = pretty.read_text(encoding="utf-8")
    assert json.loads(compact_text) == json.loads(pretty_text)
    assert '"format":"meshcad-cfd-mesh"' in compact_text
    assert '\n  "format"' in pretty_text
    assert len(compact_text) < len(pretty_text)


def test_periodic_face_pairs_are_exported():
    boundaries = BoundaryModel()
    source = boundaries.add_patch("periodic-left", "periodic")
    target = boundaries.add_patch("periodic-right", "periodic")
    pair = boundaries.add_periodic_pair("left-right", source.id, target.id)
    mesh = _square_mesh(source.id)
    faces = list(mesh.faces)
    faces[1] = CfdFace(1, faces[1].node_ids, 0, patch_id=target.id)
    faces[2] = CfdFace(2, faces[2].node_ids, 0, patch_id=target.id)
    mesh = CfdMesh(mesh.nodes, mesh.cells, tuple(faces), (PeriodicFaceLink(pair.id, 3, 1, False),))
    data = cfd_mesh_to_dict(mesh, boundaries)
    assert data["periodic_pairs"] == [{
        "id": pair.id, "name": "left-right", "source_patch": source.id,
        "target_patch": target.id, "face_pairs": [[3, 1, False]],
    }]


def test_invalid_topology_is_rejected():
    mesh = _square_mesh()
    bad_faces = mesh.faces[:3]
    with pytest.raises(CfdMeshExportError, match="four distinct faces"):
        cfd_mesh_to_dict(CfdMesh(mesh.nodes, mesh.cells, bad_faces), _wall_boundaries())

    unpatched = tuple(CfdFace(face.id, face.node_ids, face.owner) for face in mesh.faces)
    with pytest.raises(CfdMeshExportError, match="not assigned"):
        cfd_mesh_to_dict(CfdMesh(mesh.nodes, mesh.cells, unpatched), _wall_boundaries())
