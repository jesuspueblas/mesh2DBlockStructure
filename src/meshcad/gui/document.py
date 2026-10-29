"""Document: project state (topology, mesh, and blocks)."""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from typing import Any, Dict, List, Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QUndoStack

from meshcad.core.boundary import PatchModel
from meshcad.core.geometry.entity import GeometryEntity
from meshcad.core.geometry.point import Point2D
from meshcad.core.geometry.spline import Spline
from meshcad.core.mesh.generator import BlockMesh, mesh_block
from meshcad.core.mesh.model import (
    DEFAULT_N_NODES,
    EdgeMeshSpec,
    MeshModel,
    UniformDistribution,
)
from meshcad.core.mesh.smoothing import SmoothingOptions
from meshcad.core.topology.block import Block
from meshcad.core.topology.block_side import BlockSide
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

    def split_edge_at_point(
        self, edge_id: int, point: Point2D, tolerance: Optional[float] = None
    ) -> Tuple[Edge, Edge]:
        if not math.isfinite(point.x) or not math.isfinite(point.y):
            raise ValueError("Split coordinates must be finite.")
        parameter, _, distance = self.topology.closest_point_on_edge(
            edge_id, point
        )
        if tolerance is not None and (
            not math.isfinite(tolerance) or tolerance < 0
        ):
            raise ValueError("Split-point tolerance must be finite and non-negative.")
        if tolerance is not None and distance > tolerance:
            raise ValueError("The split point must lie on the selected edge.")
        if parameter <= 1e-7 or parameter >= 1.0 - 1e-7:
            raise ValueError("The split point must be strictly inside the edge.")
        return self.split_edge(edge_id, parameter)

    def split_edge(self, edge_id: int, parameter: float) -> Tuple[Edge, Edge]:
        edge = self.topology.get_edge(edge_id)
        first_geometry, second_geometry = self.topology.split_geometries(
            edge.geometry, parameter
        )
        second_edge_id = self.topology.next_edge_id
        old_spec = self.mesh.get_spec(edge_id)
        total_intervals = old_spec.n_nodes
        length_fraction = first_geometry.length() / (
            first_geometry.length() + second_geometry.length()
        )
        first_intervals = max(
            1,
            min(
                total_intervals - 1,
                int(round(total_intervals * length_fraction)),
            ),
        )
        second_intervals = total_intervals - first_intervals
        first_spec = EdgeMeshSpec(
            edge_id, first_intervals + 1, old_spec.distribution
        )
        second_spec = EdgeMeshSpec(
            second_edge_id, second_intervals + 1, old_spec.distribution
        )

        candidate_blocks: List[Block] = []
        for block in self.blocks:
            candidate_sides: List[BlockSide] = []
            for side in block.sides:
                replaced_edges = self.topology.replace_edge_in_side(
                    side, edge_id, second_edge_id
                )
                candidate_sides.append(
                    BlockSide(replaced_edges, side.node_count)
                )
            candidate_blocks.append(Block(block.id, tuple(candidate_sides)))

        candidate_geometries = {
            current.id: current.geometry for current in self.topology.edges()
        }
        candidate_geometries[edge_id] = first_geometry
        candidate_geometries[second_edge_id] = second_geometry
        candidate_specs = self._balance_block_sides(
            candidate_blocks,
            candidate_geometries,
            {**self.mesh.edge_specs, edge_id: first_spec, second_edge_id: second_spec},
        )
        self._validate_block_mesh_counts(candidate_blocks, candidate_specs)

        first_edge, second_edge = self.topology.split_edge(edge_id, parameter)
        for block in self.blocks:
            for side in block.sides:
                side.oriented_edges = self.topology.replace_edge_in_side(
                    side, edge_id, second_edge.id
                )
        for spec in candidate_specs.values():
            self.mesh.set_spec(spec)
        self.patches.replace_edge(edge_id, (edge_id, second_edge.id))
        self.patches_changed.emit()
        self.mesh_changed.emit()
        self.notify_change()
        return first_edge, second_edge

    def _balance_block_sides(
        self,
        blocks: List[Block],
        geometries: Dict[int, GeometryEntity],
        specs: Dict[int, EdgeMeshSpec],
    ) -> Dict[int, EdgeMeshSpec]:
        balanced = dict(specs)

        def intervals(side):
            return sum(
                balanced.get(
                    oriented.edge_id,
                    EdgeMeshSpec(
                        oriented.edge_id,
                        DEFAULT_N_NODES,
                        UniformDistribution(),
                    ),
                ).n_nodes - 1
                for oriented in side.oriented_edges
            )

        for _ in range(1000):
            changed = False
            for block in blocks:
                for first_index, second_index in ((0, 2), (1, 3)):
                    first_side = block.sides[first_index]
                    second_side = block.sides[second_index]
                    first_count = intervals(first_side)
                    second_count = intervals(second_side)
                    if first_count == second_count:
                        continue

                    side = first_side if first_count < second_count else second_side
                    difference = abs(first_count - second_count)
                    if not side.oriented_edges:
                        raise ValueError(
                            "Cannot preserve block mesh counts after splitting this edge."
                        )
                    edge_id = max(
                        (oriented.edge_id for oriented in side.oriented_edges),
                        key=lambda candidate: (
                            geometries[candidate].length(), -candidate
                        ),
                    )
                    current = balanced.get(
                        edge_id,
                        EdgeMeshSpec(
                            edge_id, DEFAULT_N_NODES, UniformDistribution()
                        ),
                    )
                    balanced[edge_id] = EdgeMeshSpec(
                        edge_id, current.n_nodes + difference, current.distribution
                    )
                    changed = True
            if not changed:
                return balanced
        raise ValueError(
            "Cannot balance connected block mesh sides after splitting this edge."
        )

    def _validate_block_mesh_counts(
        self,
        blocks: Optional[List[Block]] = None,
        specs: Optional[Dict[int, EdgeMeshSpec]] = None,
    ) -> None:
        blocks = self.blocks if blocks is None else blocks
        specs = self.mesh.edge_specs if specs is None else specs

        def node_count(side: BlockSide) -> int:
            return sum(
                specs.get(
                    oriented.edge_id,
                    EdgeMeshSpec(
                        oriented.edge_id,
                        DEFAULT_N_NODES,
                        UniformDistribution(),
                    ),
                ).n_nodes - 1
                for oriented in side.oriented_edges
            ) + 1

        for block in blocks:
            for first_index, second_index in ((0, 2), (1, 3)):
                first_count = node_count(block.sides[first_index])
                second_count = node_count(block.sides[second_index])
                if first_count != second_count:
                    raise ValueError(
                        "Could not preserve block {} mesh counts after splitting: "
                        "sides {} and {} have {} and {} nodes.".format(
                            block.id,
                            first_index,
                            second_index,
                            first_count,
                            second_count,
                        )
                    )

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

    def _propagated_edge_specs(
        self, requested_specs: List[EdgeMeshSpec]
    ) -> Dict[int, EdgeMeshSpec]:
        """Return a consistent set of edge specs without mutating the document."""
        requested_by_id = {spec.edge_id: spec for spec in requested_specs}
        if len(requested_by_id) != len(requested_specs):
            raise ValueError("An edge can only have one requested mesh specification.")

        topology_edges = {edge.id: edge for edge in self.topology.edges()}
        referenced_edge_ids = {
            edge_id
            for block in self.blocks
            for side in block.sides
            for edge_id in side.edge_ids()
        }
        all_edge_ids = set(topology_edges) | referenced_edge_ids | set(requested_by_id)
        original_specs = {
            edge_id: self.mesh.get_spec(edge_id)
            for edge_id in all_edge_ids
        }
        specs = dict(original_specs)
        specs.update(requested_by_id)
        fixed_edge_ids = set(requested_by_id)
        edge_lengths = {
            edge_id: (
                topology_edges[edge_id].geometry.length()
                if edge_id in topology_edges
                else 1.0
            )
            for edge_id in all_edge_ids
        }

        def intervals(side: BlockSide) -> int:
            return sum(specs[oriented.edge_id].n_nodes - 1 for oriented in side.oriented_edges)

        def distribute_intervals(total: int, edge_ids: List[int]) -> Dict[int, int]:
            if total < len(edge_ids):
                raise ValueError(
                    "The opposite block side needs at least one interval per edge."
                )
            weights = {
                edge_id: max(edge_lengths[edge_id], 1e-12)
                for edge_id in edge_ids
            }
            weight_sum = sum(weights.values())
            remaining = total - len(edge_ids)
            exact = {
                edge_id: remaining * weights[edge_id] / weight_sum
                for edge_id in edge_ids
            }
            allocation = {
                edge_id: 1 + math.floor(exact[edge_id])
                for edge_id in edge_ids
            }
            leftover = total - sum(allocation.values())
            ranked = sorted(
                edge_ids,
                key=lambda edge_id: (
                    -(exact[edge_id] - math.floor(exact[edge_id])),
                    edge_id,
                ),
            )
            for edge_id in ranked[:leftover]:
                allocation[edge_id] += 1
            return allocation

        pending = deque(requested_by_id)
        processed = set()
        affected_pairs = set()
        max_steps = max(100, 20 * (len(all_edge_ids) + len(self.blocks)))
        steps = 0

        while pending:
            edge_id = pending.popleft()
            for block in self.blocks:
                for side_index, side in enumerate(block.sides):
                    if edge_id not in side.edge_ids():
                        continue
                    opposite_index = (side_index + 2) % 4
                    opposite = block.sides[opposite_index]
                    pair_key = (
                        block.id,
                        min(side_index, opposite_index),
                        max(side_index, opposite_index),
                    )
                    affected_pairs.add(pair_key)
                    source_total = intervals(side)
                    target_ids = opposite.edge_ids()
                    state = (
                        *pair_key,
                        side_index,
                        source_total,
                        tuple((target_id, specs[target_id].n_nodes - 1) for target_id in target_ids),
                    )
                    if state in processed:
                        continue
                    processed.add(state)
                    if intervals(opposite) == source_total:
                        continue

                    adjustable_ids = [
                        target_id
                        for target_id in target_ids
                        if target_id not in fixed_edge_ids
                    ]
                    fixed_intervals = sum(
                        specs[target_id].n_nodes - 1
                        for target_id in target_ids
                        if target_id in fixed_edge_ids
                    )
                    intervals_to_distribute = source_total - fixed_intervals
                    if not adjustable_ids:
                        raise ValueError(
                            "The requested node counts conflict with block {} sides "
                            "{} and {}.".format(
                                block.id, side_index, opposite_index
                            )
                        )

                    allocation = distribute_intervals(
                        intervals_to_distribute, adjustable_ids
                    )
                    for target_id, interval_count in allocation.items():
                        current = specs[target_id]
                        updated = EdgeMeshSpec(
                            target_id, interval_count + 1, current.distribution
                        )
                        if updated.n_nodes != current.n_nodes:
                            specs[target_id] = updated
                            pending.append(target_id)
                            steps += 1
                            if steps > max_steps:
                                raise ValueError(
                                    "Could not reconcile mesh node counts across "
                                    "the connected blocks."
                                )

        blocks_by_id = {block.id: block for block in self.blocks}
        for block_id, first_index, second_index in affected_pairs:
            block = blocks_by_id[block_id]
            if intervals(block.sides[first_index]) != intervals(block.sides[second_index]):
                raise ValueError(
                    "Could not preserve block {} mesh counts on opposite sides."
                    .format(block.id)
                )
        return {
            edge_id: spec
            for edge_id, spec in specs.items()
            if edge_id in requested_by_id or spec != original_specs[edge_id]
        }

    def set_edge_spec(self, spec: EdgeMeshSpec) -> None:
        self.set_edge_specs([spec])

    def _apply_edge_specs(self, specs: List[EdgeMeshSpec]) -> None:
        propagated_specs = self._propagated_edge_specs(specs)
        for edge_id, spec in propagated_specs.items():
            self.mesh.set_spec(spec)
        self.mesh_changed.emit()
        self.patches_changed.emit()
        self.recompute_blocks()
        if self.block_meshes:
            self.generate_mesh()

    def set_edge_specs(self, specs: List[EdgeMeshSpec]) -> None:
        self._apply_edge_specs(specs)

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
