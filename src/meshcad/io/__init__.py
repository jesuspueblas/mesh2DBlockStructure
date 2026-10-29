"""JSON persistence and VTK export.

This package does not depend on PyQt5. Conversion between dictionaries
and Document objects belongs to the GUI layer.
"""

from meshcad.io.json_io import (
    block_from_dict,
    patch_model_from_dict,
    patch_model_to_dict,
    mesh_patch_from_dict,
    mesh_patch_to_dict,
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
    "mesh_patch_to_dict",
    "mesh_patch_from_dict",
    "patch_model_to_dict",
    "patch_model_from_dict",
    "save_project",
    "load_project",
    "export_mesh_vtk",
]
