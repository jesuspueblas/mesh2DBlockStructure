"""Public neutral name for the mesh-patch editor panel.

The implementation remains in ``boundaries_panel`` temporarily so projects
and imports from earlier MeshCAD versions can migrate without a disruptive
file rename.
"""
from meshcad.gui.boundaries_panel import BoundariesPanel

__all__ = ["BoundariesPanel"]
