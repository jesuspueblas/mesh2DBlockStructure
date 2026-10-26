"""Boundary-model validation results."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class BoundaryIssueCode(str, Enum):
    EMPTY_PATCH = "empty_patch"
    UNKNOWN_EDGE = "unknown_edge"
    INTERNAL_EDGE = "internal_edge"
    NON_MANIFOLD_EDGE = "non_manifold_edge"
    UNASSIGNED_EXTERNAL_EDGE = "unassigned_external_edge"


@dataclass(frozen=True, order=True)
class BoundaryValidationIssue:
    code: BoundaryIssueCode
    message: str
    patch_id: int | None = None
    edge_id: int | None = None


@dataclass(frozen=True)
class BoundaryValidationResult:
    issues: Tuple[BoundaryValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.issues
