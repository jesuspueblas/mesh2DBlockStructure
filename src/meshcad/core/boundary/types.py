"""Boundary-condition categories understood by the mesh generator."""
from __future__ import annotations

from enum import Enum


class BoundaryType(str, Enum):
    """Topological boundary categories exported by MeshCAD.

    Detailed physical models such as no-slip or pressure outlet belong to the
    CFD solver configuration, not to the mesh project.
    """

    WALL = "wall"
    INLET = "inlet"
    OUTLET = "outlet"
    PERIODIC = "periodic"
