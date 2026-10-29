"""Document: project state (topology, mesh, and blocks)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Dict, List, Tuple

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QUndoStack

from meshcad.core.boundary import PatchModel
from meshcad.core.geometry.point import Point2D
from meshcad.core.geometry.spline import Spline
from meshcad.core.mesh.generator import BlockMesh, mesh_block
from meshcad.core.mesh.model import EdgeMeshSpec, MeshModel, UniformDistribution
from meshcad.core.mesh.smoothing import SmoothingOptions
from meshcad.core.topology.block import Block
from meshcad.core.topology.edge import Edge
from meshcad.core.topology.topology import Topology
from meshcad.core.topology.usage import external_edge_ids

FORMAT = "meshcad-project"
FORMAT_VERSION = 3


class Document(QObject):
    topology_changed = pyqtSignal()
    mesh_changed = pyqtSignal()
    blocks_changed = pyqtSignal()
    patches_changed = pyqtSignal()
    mesh_generated = pyqtSignal()
    project_replaced = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.topology = Topology()
        self.patches = PatchModel()
        self.mesh = MeshModel()
        self.blocks: List[Block] = []
        self.block_meshes: List[BlockMesh] = []
        self._next_block_id = 0
        self.undo_stack = QUndoStack()
        self.mesh_improvement = SmoothingOptions()

    def notify_change(self) -> None:
        self.topology_changed.emit()
        self.recompute_blocks()
        if self.block_meshes:
            self.generate_mesh()

    def next_block_id(self) -> int:
        bid = self._next_block_id
        self._next_block_id += 1
        return bid

    def add_block(self, block: Block) -> None:
        self.blocks.append(block)
        self.recompute_blocks()

    def add_point_sequence(self, points: Sequence[Point2D]) -> Edge:
        """Add an ordered point sequence as one interpolating spline edge."""
        if len(points) < 2:
            raise ValueError("The point sequence must contain at least two points.")
        if any(
            not math.isfinite(point.x)
            or not math.isfinite(point.y)
            for point in points
        ):
            raise ValueError("Point coordinates must be finite.")

        first_vertex = self.topology.find_vertex_at(points[0])
        last_vertex = self.topology.find_vertex_at(points[-1])
        spline_points = list(points)
        if first_vertex is not None:
            spline_points[0] = first_vertex.point
        if last_vertex is not None:
            spline_points[-1] = last_vertex.point
        if any(a == b for a, b in zip(spline_points, spline_points[1:])):
            raise ValueError(
                "Consecutive points must be distinct after connecting to existing vertices."
            )

        geometry = Spline(tuple(spline_points))
        if first_vertex is None:
            first_vertex = self.topology.add_vertex(geometry.start_point())
        if last_vertex is None:
            last_vertex = self.topology.add_vertex(geometry.end_point())
        edge = self.topology.add_edge(first_vertex, last_vertex, geometry)
        self.notify_change()
        return edge

    def remove_block(self, block_id: int) -> None:
        self.blocks = [b for b in self.blocks if b.id != block_id]
        self.recompute_blocks()
        if self.block_meshes:
            self.generate_mesh()
        self.blocks_changed.emit()

    def remove_edges(self, edge_ids: list) -> tuple:
        success = 0
        fail = 0
        for eid in edge_ids:
            in_block = False
            for b in self.blocks:
                for side in b.sides:
                    if eid in side.edge_ids():
                        in_block = True
                        break
                if in_block:
                    break

            if in_block:
                fail += 1
            else:
                self.topology.remove_edge(eid)
                self.mesh.clear_spec(eid)
                self.patches.discard_edges([eid])
                success += 1

        if success > 0:
            self.patches_changed.emit()
            self.notify_change()
        return success, fail

    def recompute_blocks(self) -> None:
        for block in self.blocks:
            for side in block.sides:
                side.node_count = self.mesh.side_node_count(side)
        self.blocks_changed.emit()


    # ---------------------------- boundaries ---------------------------- #

    def add_mesh_patch(self, name: str):
        patch = self.patches.add_patch(name)
        self.patches_changed.emit()
        return patch

    def remove_mesh_patch(self, patch_id: int):
        patch = self.patches.remove_patch(patch_id)
        self.patches_changed.emit()
        return patch

    def rename_mesh_patch(self, patch_id: int, name: str):
        patch = self.patches.rename_patch(patch_id, name)
        self.patches_changed.emit()
        return patch

    def assign_mesh_patch_edges(self, patch_id: int, edge_ids):
        requested_edge_ids = set(map(int, edge_ids))
        existing_edge_ids = {edge.id for edge in self.topology.edges()}
        unknown_edge_ids = requested_edge_ids - existing_edge_ids
        if unknown_edge_ids:
            raise ValueError(
                "Cannot assign unknown edge IDs to a mesh patch: {}".format(
                    ", ".join(map(str, sorted(unknown_edge_ids)))
                )
            )

        exterior_ids = set(external_edge_ids(self.blocks))
        invalid_edge_ids = requested_edge_ids - exterior_ids
        if invalid_edge_ids:
            raise ValueError(
                "Only exterior block edges can be assigned to mesh patches. "
                "Invalid edge IDs: {}".format(
                    ", ".join(map(str, sorted(invalid_edge_ids)))
                )
            )

        patch = self.patches.assign_edges(patch_id, requested_edge_ids)
        self.patches_changed.emit()
        return patch

    def unassign_mesh_patch_edges(self, patch_id: int, edge_ids):
        patch = self.patches.unassign_edges(patch_id, edge_ids)
        self.patches_changed.emit()
        return patch

    # ------------------------------- mesh ------------------------------- #

    def _propagate_nodes(self, edge_id: int, n_nodes: int, visited: set) -> None:
        if edge_id in visited:
            return
        visited.add(edge_id)

        spec = self.mesh.get_spec(edge_id)
        self.mesh.set_spec(EdgeMeshSpec(edge_id, n_nodes, spec.distribution))

        for block in self.blocks:
            for i, side in enumerate(block.sides):
                if edge_id in side.edge_ids():
                    opp_idx = (i + 2) % 4
                    opp_side = block.sides[opp_idx]
                    k = len(opp_side.oriented_edges)
                    if k > 0:
                        base = (n_nodes + k - 1) // k
                        for oe in opp_side.oriented_edges:
                            self._propagate_nodes(oe.edge_id, base, visited)

    def set_edge_spec(self, spec: EdgeMeshSpec) -> None:
        visited = set()
        self._propagate_nodes(spec.edge_id, spec.n_nodes, visited)
        # Ensure the original edge retains its distribution.
        self.mesh.set_spec(spec)
        self.mesh_changed.emit()
        self.patches_changed.emit()
        self.recompute_blocks()
        if self.block_meshes:
            self.generate_mesh()

    def set_edge_specs(self, specs: List[EdgeMeshSpec]) -> None:
        visited = set()
        for spec in specs:
            self._propagate_nodes(spec.edge_id, spec.n_nodes, visited)
            self.mesh.set_spec(spec)
        self.mesh_changed.emit()
        self.patches_changed.emit()
        self.recompute_blocks()
        if self.block_meshes:
            self.generate_mesh()

    def generate_mesh(self) -> Tuple[List[BlockMesh], List[str]]:
        self.block_meshes = []
        errors: List[str] = []
        for block in self.blocks:
            try:
                bm = mesh_block(block, self.topology, self.mesh, self.mesh_improvement)
            except ValueError as e:
                errors.append("Block {}: {}".format(block.id, e))
                continue
            self.block_meshes.append(bm)
        self.mesh_generated.emit()
        return self.block_meshes, errors

    def to_dict(self) -> Dict[str, Any]:
        from meshcad.io.json_io import (
            block_to_dict,
            edge_spec_to_dict,
            patch_model_to_dict,
            topology_to_dict,
        )
        return {
            "format": FORMAT,
            "version": FORMAT_VERSION,
            "topology": topology_to_dict(self.topology),
            "patches": patch_model_to_dict(self.patches),
            "edge_specs": [edge_spec_to_dict(s) for s in self.mesh.edge_specs.values()],
            "blocks": [block_to_dict(b) for b in self.blocks],
            "next_block_id": self._next_block_id,
            "mesh_improvement": self.mesh_improvement.__dict__,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        from meshcad.io.json_io import (
            block_from_dict,
            edge_spec_from_dict,
            patch_model_from_dict,
            topology_from_dict,
        )
        if data.get("format") != FORMAT:
            raise ValueError("Unknown format")
        version = int(data.get("version", 1))
        if version not in (1, 2, FORMAT_VERSION):
            raise ValueError("Unsupported project version: {}".format(version))
        doc = cls()
        doc.topology = topology_from_dict(data["topology"])
        doc.patches = patch_model_from_dict(data.get("patches", data.get("boundaries", {})))
        for sd in data.get("edge_specs", []):
            doc.mesh.set_spec(edge_spec_from_dict(sd))
        doc.blocks = [block_from_dict(bd) for bd in data.get("blocks", [])]
        doc._next_block_id = int(data.get("next_block_id", len(doc.blocks)))
        doc.mesh_improvement = SmoothingOptions(**data.get("mesh_improvement", {}))
        doc.recompute_blocks()
        return doc

    def load_from(self, other: "Document") -> None:
        self.topology = other.topology
        self.patches = other.patches
        self.mesh = other.mesh
        self.blocks = other.blocks
        self._next_block_id = other._next_block_id
        self.mesh_improvement = other.mesh_improvement
        self.block_meshes = []
        self.topology_changed.emit()
        self.mesh_changed.emit()
        self.patches_changed.emit()
        self.recompute_blocks()
        self.project_replaced.emit()
