# MeshCAD Architecture

## Overview

```text
+------------------+     +------------------+     +------------------+
|   core (pure)    |<----|       gui        |<----|        io        |
|  geometry /      |     |  canvas, tools,  |     |  JSON, VTK       |
|  topology /      |     |  panels, doc     |     |  (plain dicts)   |
|  mesh            |     |  (PyQt5)         |     |                  |
+------------------+     +------------------+     +------------------+
         ^                        ^                       ^
         |                        |                       |
         +--------- no dependency on Qt ----------------+
```

Dependency rules:

- `core` does **not** import PyQt5, `gui`, or `io`.
- `gui` may import `core` and `io`. It is the only layer that knows about Qt.
- `io` may import `core`. It does **not** import `gui` and works with plain dictionaries.

## Packages

### `meshcad.core.geometry`

- `Point2D` and `Vector2D` provide immutable 2D primitives.
- `GeometryEntity` defines the common geometry interface.
- `Line`, `Arc`, and `Spline` implement the supported CAD entities.
- `evaluate(t) -> Point2D` uses a normalized parameter in `[0, 1]`.
- Geometry entities expose bounding boxes, sampling, endpoints, and editable grips.

### `meshcad.core.topology`

- `Vertex`, `Edge`, and `OrientedEdge` use identifiers that are unique within a `Topology`.
- `Topology` stores vertices and edges and assigns monotonically increasing IDs.
- `Loop` represents a closed contour and stores references by ID rather than copies.
- `BlockSide` represents one logical side and may contain one or more oriented edges.
- `Block` represents a four-sided structured block.
- `loop_detector` detects simple closed loops automatically.
- Moving a shared vertex updates every connected edge.
- Moving an arc center or spline grip is handled through the topology layer so connectivity is preserved.

### `meshcad.core.mesh`

- `NodeDistribution` is the distribution interface.
- `UniformDistribution` creates equally spaced parameter positions.
- `BiasedDistribution` creates geometrically graded spacing.
- `EdgeMeshSpec` stores `(edge_id, n_nodes, distribution)`.
- `MeshModel` maps each edge ID to one mesh specification.
- `tfi_grid` performs transfinite interpolation for a quadrilateral.
- `mesh_block` combines a `Block`, `MeshModel`, and `Topology` to produce a `BlockMesh`.
- The smoothing module supports near-boundary orthogonality and elliptic smoothing while keeping boundary nodes fixed.

### `meshcad.gui`

- `Document` owns project state, topology, mesh settings, blocks, generated meshes, and serialization.
- `CadCanvas` is a `QGraphicsView` with previews, snapping, selection, dragging, zoom, pan, and fit-to-model behavior.
- `tools/` contains `LineTool`, `ArcTool`, `SplineTool`, and `CornerPicker`.
- `LoopsPanel` detects and selects closed contours.
- `MeshPanel` edits edge distributions and node counts.
- `BlocksPanel` reports block dimensions and opposite-side compatibility.
- `MainWindow` coordinates menus, the toolbar, panels, status messages, project I/O, and VTK export.

### `meshcad.io`

- JSON serialization converts geometry, topology, mesh specifications, blocks, and settings to and from plain dictionaries.
- VTK export writes one `.vts` structured-grid file per block and one `.pvd` collection file.
- This package contains no Qt dependencies.

## Data Ownership

- The topology owns vertices and edges.
- An edge owns its geometry entity but refers to its endpoint vertices by ID.
- Loops and block sides refer to existing edges through oriented edge references.
- `MeshModel` owns one distribution specification per edge.
- `Document` coordinates all subsystems and emits change notifications to the GUI.
- Generated block meshes are derived data and can be regenerated from project state.

## Main Workflow

1. The user creates connected CAD geometry.
2. The loop detector finds closed contours.
3. Four selected loop vertices define the logical block corners.
4. The contour segments between consecutive corners become the four block sides.
5. Edge distributions determine boundary-node positions.
6. Opposite sides are validated for compatible total node counts.
7. Transfinite interpolation generates the interior grid.
8. Optional orthogonality and elliptic smoothing improve interior-node placement.
9. The generated block meshes can be displayed or exported to VTK.

## Block and Edge Compatibility

A structured block requires equal total node counts on opposite sides:

- side 0 must match side 2;
- side 1 must match side 3.

A side may contain several edges. Shared vertices between consecutive edges are counted only once. When an edge specification changes, MeshCAD propagates compatible totals to the opposite side where possible. A shared edge has a single `EdgeMeshSpec`, so adjacent blocks automatically use the same interface nodes.

## Geometry Editing

- Topological vertices are edited by dragging or by entering exact coordinates.
- Dragging a vertex near another unconnected vertex highlights the target and merges the vertices on release.
- Arc centers and internal spline points are represented as grips.
- Arc endpoint edits recompute radius and angles while preserving connectivity.
- Arc-center edits keep endpoints fixed and project the requested center onto the chord perpendicular bisector.
- If generated meshes exist, geometry and parameter changes trigger mesh regeneration.

## Persistence

The JSON project format stores:

- vertices and their stable IDs;
- edges and geometry-specific data;
- edge mesh specifications;
- block-side orientation and block composition;
- orthogonality and smoothing settings.

Generated mesh coordinates are derived and do not need to be the authoritative project state.

## Testing Strategy

The test suite covers:

- geometry evaluation, bounds, and grips;
- topology connectivity and loop detection;
- node distributions, TFI, orthogonality, and smoothing;
- JSON round trips and ID preservation;
- VTK multiblock export;
- GUI panels, toolbar actions, tooltips, reset zoom, and double-click editing.

Run all tests with:

```bash
python -m pytest -q
```
