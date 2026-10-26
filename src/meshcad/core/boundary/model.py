"""Boundary-condition collection and its invariants."""
from __future__ import annotations

from dataclasses import replace
from typing import Dict, Iterable, Tuple

from meshcad.core.boundary.patch import BoundaryPatch
from meshcad.core.boundary.types import BoundaryType
from meshcad.core.boundary.validation import (
    BoundaryIssueCode,
    BoundaryValidationIssue,
    BoundaryValidationResult,
)
from meshcad.core.topology.usage import find_edge_uses


class BoundaryModel:
    """Own named boundary patches and enforce unique edge assignment."""

    def __init__(self) -> None:
        self._patches: Dict[int, BoundaryPatch] = {}
        self._next_patch_id = 0

    @property
    def next_patch_id(self) -> int:
        return self._next_patch_id

    def patches(self) -> Tuple[BoundaryPatch, ...]:
        return tuple(self._patches[patch_id] for patch_id in sorted(self._patches))

    def get_patch(self, patch_id: int) -> BoundaryPatch:
        try:
            return self._patches[int(patch_id)]
        except KeyError as exc:
            raise KeyError("Unknown boundary patch id: {}".format(patch_id)) from exc

    def patch_for_edge(self, edge_id: int) -> BoundaryPatch | None:
        edge_id = int(edge_id)
        for patch in self.patches():
            if edge_id in patch.edge_ids:
                return patch
        return None

    def add_patch(self, name: str, boundary_type: BoundaryType | str) -> BoundaryPatch:
        normalized_name = self._validate_unique_name(name)
        patch = BoundaryPatch(
            id=self._next_patch_id,
            name=normalized_name,
            boundary_type=BoundaryType(boundary_type),
        )
        self._patches[patch.id] = patch
        self._next_patch_id += 1
        return patch

    def remove_patch(self, patch_id: int) -> BoundaryPatch:
        patch = self.get_patch(patch_id)
        del self._patches[patch.id]
        return patch

    def rename_patch(self, patch_id: int, name: str) -> BoundaryPatch:
        patch = self.get_patch(patch_id)
        normalized_name = self._validate_unique_name(name, exclude_id=patch.id)
        updated = replace(patch, name=normalized_name)
        self._patches[patch.id] = updated
        return updated

    def set_patch_type(
        self, patch_id: int, boundary_type: BoundaryType | str
    ) -> BoundaryPatch:
        patch = self.get_patch(patch_id)
        updated = replace(patch, boundary_type=BoundaryType(boundary_type))
        self._patches[patch.id] = updated
        return updated

    def assign_edges(self, patch_id: int, edge_ids: Iterable[int]) -> BoundaryPatch:
        """Assign edges, moving them atomically from any previous patch."""

        patch = self.get_patch(patch_id)
        assigned = set(int(edge_id) for edge_id in edge_ids)
        if not assigned:
            return patch

        for current in self.patches():
            if current.id == patch.id:
                continue
            remaining = tuple(edge_id for edge_id in current.edge_ids if edge_id not in assigned)
            if remaining != current.edge_ids:
                self._patches[current.id] = replace(current, edge_ids=remaining)

        updated = replace(patch, edge_ids=tuple(set(patch.edge_ids) | assigned))
        self._patches[patch.id] = updated
        return updated

    def unassign_edges(self, patch_id: int, edge_ids: Iterable[int]) -> BoundaryPatch:
        patch = self.get_patch(patch_id)
        removed = set(int(edge_id) for edge_id in edge_ids)
        updated = replace(
            patch,
            edge_ids=tuple(edge_id for edge_id in patch.edge_ids if edge_id not in removed),
        )
        self._patches[patch.id] = updated
        return updated

    def discard_edges(self, edge_ids: Iterable[int]) -> None:
        """Remove deleted CAD edges from every patch without raising errors."""

        removed = set(int(edge_id) for edge_id in edge_ids)
        for patch in self.patches():
            remaining = tuple(edge_id for edge_id in patch.edge_ids if edge_id not in removed)
            if remaining != patch.edge_ids:
                self._patches[patch.id] = replace(patch, edge_ids=remaining)

    def validate(self, blocks: Iterable[object]) -> BoundaryValidationResult:
        usage = find_edge_uses(blocks)
        external = {edge_id for edge_id, uses in usage.items() if len(uses) == 1}
        internal = {edge_id for edge_id, uses in usage.items() if len(uses) == 2}
        non_manifold = {edge_id for edge_id, uses in usage.items() if len(uses) > 2}
        assigned = set()
        issues = []

        for patch in self.patches():
            if not patch.edge_ids:
                issues.append(BoundaryValidationIssue(
                    BoundaryIssueCode.EMPTY_PATCH,
                    "Boundary patch '{}' contains no edges".format(patch.name),
                    patch_id=patch.id,
                ))
            for edge_id in patch.edge_ids:
                assigned.add(edge_id)
                if edge_id not in usage:
                    issues.append(BoundaryValidationIssue(
                        BoundaryIssueCode.UNKNOWN_EDGE,
                        "Edge {} is not used by any block".format(edge_id),
                        patch_id=patch.id,
                        edge_id=edge_id,
                    ))
                elif edge_id in internal:
                    issues.append(BoundaryValidationIssue(
                        BoundaryIssueCode.INTERNAL_EDGE,
                        "Edge {} is an internal block interface".format(edge_id),
                        patch_id=patch.id,
                        edge_id=edge_id,
                    ))
                elif edge_id in non_manifold:
                    issues.append(BoundaryValidationIssue(
                        BoundaryIssueCode.NON_MANIFOLD_EDGE,
                        "Edge {} is used by more than two blocks".format(edge_id),
                        patch_id=patch.id,
                        edge_id=edge_id,
                    ))

        for edge_id in sorted(external - assigned):
            issues.append(BoundaryValidationIssue(
                BoundaryIssueCode.UNASSIGNED_EXTERNAL_EDGE,
                "External edge {} has no boundary patch".format(edge_id),
                edge_id=edge_id,
            ))

        return BoundaryValidationResult(tuple(sorted(issues)))

    def _validate_unique_name(self, name: str, exclude_id: int | None = None) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValueError("Boundary patch name must not be empty")
        folded = normalized.casefold()
        for patch in self.patches():
            if patch.id != exclude_id and patch.name.casefold() == folded:
                raise ValueError("Boundary patch name already exists: {}".format(normalized))
        return normalized

    @classmethod
    def restore(
        cls, patches: Iterable[BoundaryPatch], next_patch_id: int | None = None
    ) -> "BoundaryModel":
        model = cls()
        for patch in patches:
            if patch.id in model._patches:
                raise ValueError("Duplicate boundary patch id: {}".format(patch.id))
            model._validate_unique_name(patch.name)
            for edge_id in patch.edge_ids:
                owner = model.patch_for_edge(edge_id)
                if owner is not None:
                    raise ValueError(
                        "Edge {} belongs to more than one boundary patch".format(edge_id)
                    )
            model._patches[patch.id] = patch
        minimum = max(model._patches, default=-1) + 1
        if next_patch_id is None:
            model._next_patch_id = minimum
        else:
            model._next_patch_id = int(next_patch_id)
            if model._next_patch_id < minimum:
                raise ValueError("next_patch_id is smaller than an existing patch id")
        return model
