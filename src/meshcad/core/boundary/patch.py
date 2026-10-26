"""Boundary patch value object."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from meshcad.core.boundary.types import BoundaryType


@dataclass(frozen=True)
class BoundaryPatch:
    """A named group of exterior CAD edges with one boundary category."""

    id: int
    name: str
    boundary_type: BoundaryType
    edge_ids: Tuple[int, ...] = ()

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("Boundary patch name must not be empty")
        if name != self.name:
            object.__setattr__(self, "name", name)
        normalized = tuple(sorted(set(int(edge_id) for edge_id in self.edge_ids)))
        object.__setattr__(self, "edge_ids", normalized)
