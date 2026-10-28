"""Finite-volume connectivity assembled from conformal structured block meshes."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from meshcad.core.boundary import PatchModel
from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.generator import BlockMesh
from meshcad.core.mesh.model import MeshModel
from meshcad.core.topology.block import Block
from meshcad.core.topology.topology import Topology


@dataclass(frozen=True)
class CfdCell:
    id: int
    node_ids: Tuple[int, int, int, int]
    block_id: int
    i: int
    j: int
    area: float


@dataclass(frozen=True)
class CfdFace:
    id: int
    node_ids: Tuple[int, int]
    owner: int
    neighbour: int | None = None
    patch_id: int | None = None
    cad_edge_id: int | None = None

    @property
    def is_boundary(self) -> bool:
        return self.neighbour is None


@dataclass(frozen=True)
class CfdMesh:
    nodes: Tuple[Point2D, ...]
    cells: Tuple[CfdCell, ...]
    faces: Tuple[CfdFace, ...]

    @property
    def internal_faces(self) -> Tuple[CfdFace, ...]:
        return tuple(face for face in self.faces if not face.is_boundary)

    @property
    def boundary_faces(self) -> Tuple[CfdFace, ...]:
        return tuple(face for face in self.faces if face.is_boundary)

    def faces_for_patch(self, patch_id: int) -> Tuple[CfdFace, ...]:
        return tuple(face for face in self.boundary_faces if face.patch_id == patch_id)


class ConnectivityError(ValueError):
    """Raised when the block meshes cannot form a valid finite-volume mesh."""


class _NodeRegistry:
    def __init__(self, tolerance: float) -> None:
        if not math.isfinite(tolerance) or tolerance <= 0.0:
            raise ValueError("Node merge tolerance must be a positive finite number")
        self.tolerance = tolerance
        self.nodes: List[Point2D] = []
        self._buckets: Dict[Tuple[int, int], List[int]] = {}

    def _bucket(self, point: Point2D) -> Tuple[int, int]:
        return (math.floor(point.x / self.tolerance), math.floor(point.y / self.tolerance))

    def add(self, point: Point2D) -> int:
        bx, by = self._bucket(point)
        for ix in range(bx - 1, bx + 2):
            for iy in range(by - 1, by + 2):
                for node_id in self._buckets.get((ix, iy), ()):
                    if self.nodes[node_id].distance_to(point) <= self.tolerance:
                        return node_id
        node_id = len(self.nodes)
        self.nodes.append(point)
        self._buckets.setdefault((bx, by), []).append(node_id)
        return node_id

    def find(self, point: Point2D) -> int:
        bx, by = self._bucket(point)
        best = None
        best_distance = math.inf
        for ix in range(bx - 1, bx + 2):
            for iy in range(by - 1, by + 2):
                for node_id in self._buckets.get((ix, iy), ()):
                    distance = self.nodes[node_id].distance_to(point)
                    if distance < best_distance:
                        best, best_distance = node_id, distance
        if best is None or best_distance > self.tolerance:
            raise ConnectivityError("A CAD boundary node is absent from the generated mesh")
        return best


def _signed_area(points: Sequence[Point2D]) -> float:
    return 0.5 * sum(
        point.x * points[(index + 1) % len(points)].y
        - points[(index + 1) % len(points)].x * point.y
        for index, point in enumerate(points)
    )


def _boundary_segments(
    blocks: Sequence[Block], topology: Topology, mesh_model: MeshModel,
    registry: _NodeRegistry,
) -> Mapping[Tuple[int, int], int]:
    usage: Dict[int, int] = {}
    for block in blocks:
        for side in block.sides:
            for oriented_edge in side.oriented_edges:
                usage[oriented_edge.edge_id] = usage.get(oriented_edge.edge_id, 0) + 1
    result: Dict[Tuple[int, int], int] = {}
    for edge_id, count in usage.items():
        if count != 1:
            continue
        edge = topology.get_edge(edge_id)
        spec = mesh_model.get_spec(edge_id)
        points = spec.distribution.sample(edge.geometry, spec.n_nodes)
        node_ids = [registry.find(point) for point in points]
        for first, second in zip(node_ids, node_ids[1:]):
            key = tuple(sorted((first, second)))
            previous = result.setdefault(key, edge_id)
            if previous != edge_id:
                raise ConnectivityError("Overlapping exterior CAD edges were detected")
    return result


def build_cfd_mesh(
    block_meshes: Iterable[BlockMesh], blocks: Iterable[Block], topology: Topology,
    mesh_model: MeshModel, patches: PatchModel, tolerance: float = 1.0e-9,
) -> CfdMesh:
    """Build global nodes, quadrilateral cells, owner/neighbour faces and patches."""
    meshes = sorted(block_meshes, key=lambda mesh: mesh.block_id)
    block_list = sorted(blocks, key=lambda block: block.id)
    block_ids = {block.id for block in block_list}
    mesh_ids = {mesh.block_id for mesh in meshes}
    if block_ids != mesh_ids:
        raise ConnectivityError("Generated block meshes do not match the block model")
    validation = patches.validate(block_list)
    if not validation.is_valid:
        raise ConnectivityError("Boundary model is invalid: {}".format(validation.issues[0].message))

    registry = _NodeRegistry(tolerance)
    local_nodes: Dict[int, List[List[int]]] = {}
    cells: List[CfdCell] = []
    for mesh in meshes:
        if mesh.n_u < 2 or mesh.n_v < 2 or any(len(row) != mesh.n_u for row in mesh.grid):
            raise ConnectivityError("Block {} has an invalid structured grid".format(mesh.block_id))
        ids = [[registry.add(point) for point in row] for row in mesh.grid]
        local_nodes[mesh.block_id] = ids
        for j in range(mesh.n_v - 1):
            for i in range(mesh.n_u - 1):
                node_ids = (ids[j][i], ids[j][i + 1], ids[j + 1][i + 1], ids[j + 1][i])
                points = [registry.nodes[node_id] for node_id in node_ids]
                area = _signed_area(points)
                if abs(area) <= tolerance * tolerance:
                    raise ConnectivityError(
                        "Degenerate cell in block {} at ({}, {})".format(mesh.block_id, i, j)
                    )
                if area < 0.0:
                    node_ids = (node_ids[0], node_ids[3], node_ids[2], node_ids[1])
                    area = -area
                cells.append(CfdCell(len(cells), node_ids, mesh.block_id, i, j, area))

    face_data: Dict[Tuple[int, int], List[object]] = {}
    face_order: List[Tuple[int, int]] = []
    for cell in cells:
        for first, second in zip(cell.node_ids, cell.node_ids[1:] + cell.node_ids[:1]):
            key = tuple(sorted((first, second)))
            if key not in face_data:
                face_data[key] = [first, second, cell.id, None]
                face_order.append(key)
            elif face_data[key][3] is None:
                face_data[key][3] = cell.id
            else:
                raise ConnectivityError("A face is shared by more than two cells")

    cad_segments = _boundary_segments(block_list, topology, mesh_model, registry)
    patch_for_edge = {
        edge_id: patch.id
        for patch in patches.patches()
        for edge_id in patch.edge_ids
    }
    faces: List[CfdFace] = []
    for key in face_order:
        first, second, owner, neighbour = face_data[key]
        cad_edge_id = cad_segments.get(key) if neighbour is None else None
        patch_id = patch_for_edge.get(cad_edge_id) if cad_edge_id is not None else None
        if neighbour is None and patch_id is None:
            raise ConnectivityError("An exterior finite-volume face has no boundary patch")
        faces.append(CfdFace(len(faces), (first, second), owner, neighbour, patch_id, cad_edge_id))

    return CfdMesh(tuple(registry.nodes), tuple(cells), tuple(faces))
