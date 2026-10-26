"""Boundary conditions for structured block meshes."""

from meshcad.core.boundary.model import BoundaryModel
from meshcad.core.boundary.patch import BoundaryPatch
from meshcad.core.boundary.types import BoundaryType
from meshcad.core.boundary.validation import (
    BoundaryIssueCode,
    BoundaryValidationIssue,
    BoundaryValidationResult,
)

__all__ = [
    "BoundaryIssueCode",
    "BoundaryModel",
    "BoundaryPatch",
    "BoundaryType",
    "BoundaryValidationIssue",
    "BoundaryValidationResult",
]
