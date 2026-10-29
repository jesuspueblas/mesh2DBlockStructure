# MeshCAD User Manual

## Starting the Application

From the project root, run:

```bash
python -m meshcad
```

## Interface Overview

The main window contains:

- **File menu:** New, Open, Save, Save As, Export Mesh (VTK), and Exit.
- **Toolbar:** Select, Line, Arc, Spline, Insert Point, Generate Mesh, Clear Mesh, Show Grid, Reset Zoom, and live mesh-improvement controls.
- **Central canvas:** drawing, selection, geometry editing, zoom, pan, and mesh visualization.
- **Loops panel:** closed-loop detection and block creation.
- **Distributions panel:** edge selection, node counts, and distribution settings.
- **Blocks panel:** block dimensions and compatibility status.
- **Status bar:** operation messages and current cursor coordinates.

Hold the pointer over a toolbar icon or parameter control to display its tooltip.

## Canvas Navigation

- Rotate the **mouse wheel** to zoom around the pointer.
- Hold the **middle mouse button** and drag to pan.
- Click **Reset Zoom** to fit the complete model in the viewport.
- Press **Esc** to cancel the active drawing tool.
- Read the current scene coordinates in the status bar.

## Typical Workflow

### 1. Draw Geometry

Choose one of the CAD tools:

- **Line:** click the start point and the end point.
- **Arc:** click the center, the start point, and the end point. The arc is traversed counterclockwise.
- **Spline:** add control points with left-click and finish with right-click.
- **Insert Point:** enter exact X and Y coordinates for an isolated vertex.

A dashed preview shows the candidate geometry while the pointer moves. Existing vertices appear as light red circles. New points snap to nearby vertices so that contours can be closed accurately.

### 2. Edit Geometry

Switch to **Select** before editing.

- Drag a red vertex to move every connected edge.
- Drag a blue grip to move an arc center or an internal spline control point.
- Double-click a vertex or grip to enter exact coordinates.
- When an arc center is edited, its endpoints remain fixed and the center is constrained to the chord perpendicular bisector.
- Existing block meshes are regenerated automatically after relevant geometry changes.

### 3. Detect a Closed Loop

In the **Loops** panel, click **Detect Loops**. Closed contours are listed. Selecting a loop highlights it in green on the canvas.

If no loop is detected:

1. zoom into every connection;
2. check for gaps or duplicate endpoints;
3. use snapping or double-click coordinate editing to make endpoints coincide;
4. run **Detect Loops** again.

### 4. Create a Structured Block

Select a loop and click **Create Block from Loop**. Click four distinct loop vertices. These vertices define the four logical corners. The portions of the loop between consecutive corners become the four block sides.

A block side may contain one or several CAD edges.

### 5. Configure Edge Distributions

In the **Distributions** panel:

1. click **Refresh Edges** if necessary;
2. select one or more edges;
3. set the total number of nodes, including both endpoints;
4. choose **Uniform** or **Biased** distribution;
5. set **Bias** when a biased distribution is selected;
6. click **Apply to Selected**.

You can also select an edge by clicking it on the canvas. Hold **Ctrl** while
clicking to add or remove individual edges from the selection. A regular click
selects only that edge, and clicking empty canvas clears the selection.

A shared edge has one distribution specification, so adjacent blocks automatically use the same interface nodes.

#### Distribution Types

- **Uniform:** equal spacing in the edge parameter.
- **Biased, Bias = 1:** equivalent to uniform spacing.
- **Biased, Bias > 1:** smaller intervals near the edge start and progressively larger intervals toward the end.

### 6. Validate Blocks

The **Blocks** panel reports whether opposite sides have compatible node totals.

Typical states are:

- `OK (nodes N x M)`
- `MISMATCH sides 0/2: A vs B`
- `MISMATCH sides 1/3: A vs B`

For a valid structured block:

- side 0 must have the same total number of nodes as side 2;
- side 1 must have the same total number of nodes as side 3.

### 7. Generate the Mesh

Click **Generate Mesh**. The structured grid appears over each valid block, and the status bar reports the number of blocks and cells.

Click **Clear Mesh** to hide generated meshes without deleting geometry, blocks, or distribution settings.

## Mesh Improvement Controls

The toolbar includes live controls for mesh improvement.

### Orthogonality

Enable **Orthogonal** to push the first interior layers toward the local boundary-normal direction.

- **Layers:** number of interior layers affected.
- **Strength:** correction fraction from `0` to `1`.

Useful initial values are 2 to 4 layers and a strength from 0.70 to 0.90.

### Elliptic Smoothing

- **Smoothing:** number of interior smoothing iterations.
- **Relaxation:** update fraction per iteration.

Useful initial values are 20 to 60 iterations and a relaxation factor from 0.30 to 0.50. Boundary nodes remain fixed.

## Tutorial 1: Rectangular Block

### Objective

Create a `9 x 6` node Cartesian mesh.

### Procedure

1. Create a new project.
2. Draw line segments through `(0, 0)`, `(4, 0)`, `(4, 2.5)`, `(0, 2.5)`, and back to `(0, 0)`.
3. Detect the four-edge loop.
4. Create a block by selecting the four rectangle corners.
5. Select the bottom and top edges and apply 9 uniform nodes.
6. Select the left and right edges and apply 6 uniform nodes.
7. Confirm that the Blocks panel reports `OK (nodes 9 x 6)`.
8. Generate the mesh.

The result has `8 x 5 = 40` cells.

## Tutorial 2: Curved Two-Block Domain

### Objective

Create two conformal blocks separated by one shared edge.

### Procedure

1. Draw the left and right boundaries with splines.
2. Close the outer contour with top and bottom lines.
3. Draw a transverse line between two existing boundary vertices, snapping both endpoints.
4. Detect the upper and lower loops.
5. Create one block from each loop.
6. Assign compatible uniform distributions, for example 15 nodes on the principal edges.
7. Generate the mesh.
8. Drag a spline grip and verify that both block meshes update while the shared interface remains coincident.

The supplied `test.json` project can be used as a ready-made two-block example.

## Tutorial 3: Biased Distribution and Improvement

1. Open the curved example and generate the uniform baseline mesh.
2. Select an outer edge, choose **Biased**, and set `Bias = 1.5`.
3. Increase the node count in the direction requiring more resolution.
4. Enable **Orthogonal** with 3 layers and `Strength = 0.80`.
5. Set `Smoothing = 40` and `Relaxation = 0.40`.
6. Compare the result with orthogonality disabled and smoothing set to zero.

Inspect the grid for:

- crossed or inverted cells;
- abrupt cell-size transitions;
- irregular interior lines;
- poor boundary angles;
- discontinuities across shared block interfaces.

## Saving Projects

Use **File > Save** or **File > Save As**. The JSON project stores topology, geometry, edge distributions, blocks, and mesh-improvement parameters.

Use incremental project names before large geometry changes.

## Exporting VTK

1. Generate the mesh.
2. Choose **File > Export Mesh (VTK)**.
3. Select a `.pvd` filename.
4. MeshCAD creates the PVD file and a `<name>_blocks` folder containing one `.vts` file per block.
5. Open the `.pvd` file in ParaView to load all blocks together.

Keep the PVD file and its `_blocks` folder together because the collection uses relative paths.

## Troubleshooting

### No loop is detected

The contour is open or two endpoints do not coincide. Inspect connections and edit the affected coordinates.

### A block reports MISMATCH

Opposite sides have different total node counts. Apply compatible distribution settings to the relevant edges.

### An edge cannot be deleted

The edge belongs to a block. Delete the associated block first.

### No mesh appears

Check that at least one valid block exists and that the Blocks panel reports compatible opposite sides.

### Geometry is outside the visible area

Click **Reset Zoom**.

### The arc center is not exactly at the requested point

A circular arc with fixed endpoints requires the center to remain on the chord perpendicular bisector. MeshCAD projects the requested center onto that line.

### The mesh is strongly distorted

Reduce bias, orthogonality strength, smoothing iterations, or relaxation. Increase parameters gradually and inspect each result.

### VTK export is unavailable

Generate the mesh before exporting.

## Mouse and Keyboard Reference

- **Left-click:** place points, select an item, or begin dragging.
- **Double left-click:** edit vertex or grip coordinates.
- **Right-click:** finish a spline.
- **Middle-button drag:** pan the view.
- **Mouse wheel:** zoom around the pointer.
- **Esc:** cancel the active tool.

## Final Checklist

Before exporting a finished project, verify that:

- all intended contours are closed;
- every block reports `OK`;
- shared interfaces are conformal;
- no cells are crossed or inverted;
- grading transitions are acceptable;
- the project has been saved;
- the PVD/VTS export opens correctly.
