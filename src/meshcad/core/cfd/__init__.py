"""Finite-volume mesh connectivity derived from structured block meshes."""
from meshcad.core.cfd.connectivity import (
    CfdCell,
    CfdFace,
    CfdMesh,
    ConnectivityError,
    PeriodicFaceLink,
    build_cfd_mesh,
)

__all__ = [
    "CfdCell", "CfdFace", "CfdMesh", "ConnectivityError",
    "PeriodicFaceLink", "build_cfd_mesh",
]
