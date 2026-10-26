"""Persistencia (JSON) y exportacion (VTK).

Este paquete NO depende de PyQt5. La conversion dict <-> Document
vive en la capa de GUI.
"""

from meshcad.io.json_io import (
    block_from_dict,
    boundary_model_from_dict,
    boundary_model_to_dict,
    boundary_patch_from_dict,
    boundary_patch_to_dict,
    block_side_from_dict,
    block_side_to_dict,
    block_to_dict,
    distribution_from_dict,
    distribution_to_dict,
    edge_spec_from_dict,
    edge_spec_to_dict,
    geometry_from_dict,
    geometry_to_dict,
    topology_from_dict,
    topology_to_dict,
)
from meshcad.io.project_io import load_project, save_project
from meshcad.io.vtk_io import export_mesh_vtk

__all__ = [
    "geometry_to_dict",
    "geometry_from_dict",
    "distribution_to_dict",
    "distribution_from_dict",
    "topology_to_dict",
    "topology_from_dict",
    "edge_spec_to_dict",
    "edge_spec_from_dict",
    "block_side_to_dict",
    "block_side_from_dict",
    "block_to_dict",
    "block_from_dict",
    "boundary_patch_to_dict",
    "boundary_patch_from_dict",
    "boundary_model_to_dict",
    "boundary_model_from_dict",
    "save_project",
    "load_project",
    "export_mesh_vtk",
]
