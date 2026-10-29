"""Mesh export to VTK XML (PVD plus one VTS file per block).

The PVD (ParaView Data) format is a collection that references VTS
(VTK XML StructuredGrid) files, one per block. ParaView opens the PVD
file and displays all blocks together.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from meshcad.core.mesh.generator import BlockMesh


def export_mesh_vtk(block_meshes: List[BlockMesh], pvd_path) -> None:
    """Write a PVD file and a VTS folder containing the block meshes."""
    pvd_path = Path(pvd_path)
    pvd_path.parent.mkdir(parents=True, exist_ok=True)

    block_dir = pvd_path.parent / (pvd_path.stem + "_blocks")
    block_dir.mkdir(parents=True, exist_ok=True)

    entries: List[str] = []
    for bm in block_meshes:
        fname = "block_{:04d}.vts".format(bm.block_id)
        _write_structured_grid(block_dir / fname, bm)
        entries.append(fname)

    _write_pvd(pvd_path, entries, block_dir)


def _write_structured_grid(path: Path, bm: BlockMesh) -> None:
    grid = bm.grid
    n_v = len(grid)
    n_u = len(grid[0]) if n_v else 0

    ext = "0 {} 0 {} 0 0".format(max(n_u - 1, 0), max(n_v - 1, 0))

    coords_parts: List[str] = []
    for j in range(n_v):
        for i in range(n_u):
            p = grid[j][i]
            coords_parts.append(
                "{:.17g} {:.17g} 0".format(float(p.x), float(p.y))
            )
    coords = " ".join(coords_parts)

    xml = (
        '<?xml version="1.0"?>\n'
        '<VTKFile type="StructuredGrid" version="0.1" '
        'byte_order="LittleEndian">\n'
        '  <StructuredGrid WholeExtent="{ext}">\n'
        '    <Piece Extent="{ext}">\n'
        '      <Points>\n'
        '        <DataArray type="Float64" NumberOfComponents="3" '
        'format="ascii">\n'
        '          {coords}\n'
        '        </DataArray>\n'
        '      </Points>\n'
        '    </Piece>\n'
        '  </StructuredGrid>\n'
        '</VTKFile>\n'
    ).format(ext=ext, coords=coords)

    path.write_text(xml, encoding="utf-8")


def _write_pvd(pvd_path: Path, entries: List[str], block_dir: Path) -> None:
    rel = os.path.relpath(block_dir, pvd_path.parent).replace("\\", "/")
    rel = rel.replace("\\", "/")
    if rel == ".":
        rel = ""

    lines = [
        '<?xml version="1.0"?>',
        '<VTKFile type="Collection" version="0.1">',
        "  <Collection>",
    ]
    for i, entry in enumerate(entries):
        relpath = "{}/{}".format(rel, entry) if rel else entry
        lines.append(
            '    <DataSet timestep="0" group="" part="{}" file="{}"/>'.format(
                i, relpath
            )
        )
    lines += ["  </Collection>", "</VTKFile>", ""]
    pvd_path.write_text("\n".join(lines), encoding="utf-8")
