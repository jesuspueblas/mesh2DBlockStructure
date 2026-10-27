"""Compact JSON export of finite-volume mesh topology."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Sequence

from meshcad.core.boundary import BoundaryModel
from meshcad.core.cfd import CfdMesh

FORMAT_NAME = "meshcad-cfd-mesh"
FORMAT_VERSION = 1
NO_NEIGHBOUR = -1


class CfdMeshExportError(ValueError):
    """Raised when a CFD mesh is not topologically valid for export."""


def _ordered_ids(items: Sequence[Any], entity: str) -> None:
    actual = tuple(item.id for item in items)
    expected = tuple(range(len(items)))
    if actual != expected:
        raise CfdMeshExportError(
            f"{entity} ids must be dense and ordered from zero; got {actual}"
        )


def _cell_face_connectivity(mesh: CfdMesh) -> tuple[List[List[int]], List[List[int]]]:
    cell_faces: List[List[int]] = [[] for _ in mesh.cells]
    cell_signs: List[List[int]] = [[] for _ in mesh.cells]
    for face in mesh.faces:
        if not 0 <= face.owner < len(mesh.cells):
            raise CfdMeshExportError(f"Face {face.id} has invalid owner {face.owner}")
        cell_faces[face.owner].append(face.id)
        cell_signs[face.owner].append(1)
        if face.neighbour is not None:
            if not 0 <= face.neighbour < len(mesh.cells):
                raise CfdMeshExportError(
                    f"Face {face.id} has invalid neighbour {face.neighbour}"
                )
            if face.neighbour == face.owner:
                raise CfdMeshExportError(
                    f"Face {face.id} has identical owner and neighbour"
                )
            cell_faces[face.neighbour].append(face.id)
            cell_signs[face.neighbour].append(-1)
    for cell in mesh.cells:
        faces = cell_faces[cell.id]
        if len(faces) != 4 or len(set(faces)) != 4:
            raise CfdMeshExportError(
                f"Cell {cell.id} must reference four distinct faces; got {faces}"
            )
        expected_edges = {
            frozenset((cell.node_ids[index], cell.node_ids[(index + 1) % 4]))
            for index in range(4)
        }
        actual_edges = {frozenset(mesh.faces[face_id].node_ids) for face_id in faces}
        if actual_edges != expected_edges:
            raise CfdMeshExportError(
                f"Faces of cell {cell.id} do not form its closed node loop"
            )
    return cell_faces, cell_signs


def _patches_to_data(mesh: CfdMesh, boundaries: BoundaryModel) -> List[Dict[str, Any]]:
    known_patches = {patch.id: patch for patch in boundaries.patches()}
    patch_faces: Dict[int, List[int]] = {patch_id: [] for patch_id in known_patches}
    for face in mesh.faces:
        if face.neighbour is None:
            if face.patch_id is None:
                raise CfdMeshExportError(
                    f"Boundary face {face.id} is not assigned to a patch"
                )
            if face.patch_id not in known_patches:
                raise CfdMeshExportError(
                    f"Boundary face {face.id} references unknown patch {face.patch_id}"
                )
            patch_faces[face.patch_id].append(face.id)
        elif face.patch_id is not None:
            raise CfdMeshExportError(
                f"Internal face {face.id} must not belong to a boundary patch"
            )
    return [
        {
            "id": patch.id,
            "name": patch.name,
            "type": patch.boundary_type.value,
            "faces": patch_faces[patch.id],
        }
        for patch in boundaries.patches()
    ]


def _periodic_pairs_to_data(
    mesh: CfdMesh, boundaries: BoundaryModel
) -> List[Dict[str, Any]]:
    pair_models = {pair.id: pair for pair in boundaries.periodic_pairs()}
    links: Dict[int, List[List[Any]]] = {pair_id: [] for pair_id in pair_models}
    used_faces = set()
    for link in mesh.periodic_links:
        pair = pair_models.get(link.pair_id)
        if pair is None:
            raise CfdMeshExportError(
                f"Periodic link references unknown pair {link.pair_id}"
            )
        face_ids = (link.source_face_id, link.target_face_id)
        if any(face_id < 0 or face_id >= len(mesh.faces) for face_id in face_ids):
            raise CfdMeshExportError(
                f"Periodic pair {link.pair_id} references an invalid face"
            )
        if link.source_face_id == link.target_face_id:
            raise CfdMeshExportError(
                f"Periodic pair {link.pair_id} references the same face twice"
            )
        if any(face_id in used_faces for face_id in face_ids):
            raise CfdMeshExportError("A face belongs to more than one periodic link")
        source = mesh.faces[link.source_face_id]
        target = mesh.faces[link.target_face_id]
        if not source.is_boundary or not target.is_boundary:
            raise CfdMeshExportError("Periodic links must reference boundary faces")
        if source.patch_id != pair.source_patch_id or target.patch_id != pair.target_patch_id:
            raise CfdMeshExportError(
                f"Periodic link {link.pair_id} does not match its source/target patches"
            )
        links[link.pair_id].append(
            [link.source_face_id, link.target_face_id, bool(link.reversed)]
        )
        used_faces.update(face_ids)
    return [
        {
            "id": pair.id,
            "name": pair.name,
            "source_patch": pair.source_patch_id,
            "target_patch": pair.target_patch_id,
            "face_pairs": links[pair.id],
        }
        for pair in boundaries.periodic_pairs()
    ]


def cfd_mesh_to_dict(mesh: CfdMesh, boundaries: BoundaryModel) -> Dict[str, Any]:
    """Return the compact, versioned JSON data model for *mesh*."""
    _ordered_ids(mesh.cells, "Cell")
    _ordered_ids(mesh.faces, "Face")
    coordinates = [[float(point.x), float(point.y)] for point in mesh.nodes]
    if any(not math.isfinite(value) for point in coordinates for value in point):
        raise CfdMeshExportError("Node coordinates must be finite")
    for face in mesh.faces:
        if len(face.node_ids) != 2 or face.node_ids[0] == face.node_ids[1]:
            raise CfdMeshExportError(
                f"Face {face.id} must reference two distinct nodes"
            )
        if any(node_id < 0 or node_id >= len(mesh.nodes) for node_id in face.node_ids):
            raise CfdMeshExportError(f"Face {face.id} references an invalid node")
    for cell in mesh.cells:
        if len(cell.node_ids) != 4 or len(set(cell.node_ids)) != 4:
            raise CfdMeshExportError(
                f"Cell {cell.id} must reference four distinct nodes"
            )
        if any(node_id < 0 or node_id >= len(mesh.nodes) for node_id in cell.node_ids):
            raise CfdMeshExportError(f"Cell {cell.id} references an invalid node")

    cell_faces, cell_signs = _cell_face_connectivity(mesh)
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "dimension": 2,
        "nodes": {"coordinates": coordinates},
        "faces": {
            "nodes": [list(face.node_ids) for face in mesh.faces],
            "owner": [face.owner for face in mesh.faces],
            "neighbour": [
                NO_NEIGHBOUR if face.neighbour is None else face.neighbour
                for face in mesh.faces
            ],
        },
        "cells": {"faces": cell_faces, "face_signs": cell_signs},
        "patches": _patches_to_data(mesh, boundaries),
        "periodic_pairs": _periodic_pairs_to_data(mesh, boundaries),
    }


def write_cfd_mesh_json(
    path: str | Path,
    mesh: CfdMesh,
    boundaries: BoundaryModel,
    *,
    pretty: bool = False,
) -> None:
    """Validate and write a UTF-8 JSON mesh, compact unless *pretty* is true."""
    output = Path(path)
    data = cfd_mesh_to_dict(mesh, boundaries)
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        if pretty:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        else:
            json.dump(
                data,
                stream,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            stream.write("\n")
