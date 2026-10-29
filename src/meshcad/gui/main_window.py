"""MeshCAD main window."""

import csv
import sys
from pathlib import Path

from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QIcon, QKeySequence, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSpinBox,
    QStatusBar,
    QStyle,
    QToolBar,
    QVBoxLayout,
)

from meshcad.core.cfd import build_cfd_mesh
from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.smoothing import SmoothingOptions
from meshcad.gui.blocks_panel import BlocksPanel
from meshcad.gui.canvas import CadCanvas
from meshcad.gui.document import Document
from meshcad.gui.edges_panel import EdgesPanel
from meshcad.gui.import_points_dialog import ImportPointSequenceDialog
from meshcad.gui.loops_panel import LoopsPanel
from meshcad.gui.patches_panel import BoundariesPanel
from meshcad.gui.tools.arc_tool import ArcTool
from meshcad.gui.tools.line_tool import LineTool
from meshcad.gui.tools.spline_tool import SplineTool
from meshcad.gui.tools.split_edge_tool import SplitEdgeTool
from meshcad.io.cfd_mesh_io import write_cfd_mesh_json
from meshcad.io.point_sequence import load_point_sequence
from meshcad.io.project_io import load_project, save_project


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MeshCAD - untitled")
        self.resize(1400, 800)

        self.document = Document()
        self.current_path = None

        self.canvas = CadCanvas(self.document)
        self.setCentralWidget(self.canvas)

        self.loops_panel = LoopsPanel(self.document, self.canvas, self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.loops_panel)

        self.edges_panel = EdgesPanel(self.document, self.canvas, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.edges_panel)

        self.blocks_panel = BlocksPanel(self.document, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.blocks_panel)

        self.patches_panel = BoundariesPanel(self.document, self.edges_panel, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.patches_panel)
        self.tabifyDockWidget(self.blocks_panel, self.patches_panel)

        self.document.topology_changed.connect(self.edges_panel.refresh)
        self.document.project_replaced.connect(self._on_project_replaced)
        self.canvas.edge_clicked.connect(self._on_edge_clicked)

        status = QStatusBar()
        self.setStatusBar(status)

        self.status_label = QLabel("Ready")
        status.addWidget(self.status_label)

        self.coords_label = QLabel("X: 0.00, Y: 0.00")
        self.coords_label.setStyleSheet("padding-right: 10px;")
        status.addPermanentWidget(self.coords_label)

        self.canvas.mouse_moved.connect(self._on_mouse_moved)

        self._mesh_update_timer = QTimer(self)
        self._mesh_update_timer.setSingleShot(True)
        self._mesh_update_timer.setInterval(120)
        self._mesh_update_timer.timeout.connect(self._apply_live_mesh_options)
        self._updating_mesh_controls = False
        self._create_menus()
        self._create_toolbar()
        self.canvas.tool_changed.connect(self._on_canvas_tool_changed)
        self._on_canvas_tool_changed(self.canvas.tool)
        self._sync_mesh_controls_from_document()

    def _on_edge_clicked(self, edge_id: int, control_pressed: bool) -> None:
        if edge_id == -1:
            if not control_pressed:
                self.edges_panel.list_widget.clearSelection()
        else:
            self.edges_panel.select_edges([edge_id], toggle=control_pressed)

    def _create_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        edit_menu = self.menuBar().addMenu("&Edit")
        self.action_undo = self.document.undo_stack.createUndoAction(self, "&Undo")
        self.action_undo.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(self.action_undo)
        self.action_redo = self.document.undo_stack.createRedoAction(self, "&Redo")
        self.action_redo.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(self.action_redo)

        self.action_new = QAction("New", self)
        self.action_new.triggered.connect(self._on_new)
        file_menu.addAction(self.action_new)
        self.action_open = QAction("Open...", self)
        self.action_open.triggered.connect(self._on_open)
        file_menu.addAction(self.action_open)
        self.action_import_points = QAction("Import Point Sequence...", self)
        self.action_import_points.triggered.connect(self._on_import_point_sequence)
        file_menu.addAction(self.action_import_points)
        file_menu.addSeparator()
        self.action_save = QAction("Save", self)
        self.action_save.triggered.connect(self._on_save)
        file_menu.addAction(self.action_save)
        self.action_save_as = QAction("Save As...", self)
        self.action_save_as.triggered.connect(self._on_save_as)
        file_menu.addAction(self.action_save_as)
        file_menu.addSeparator()
        self.action_export_vtk = QAction("Export Mesh (VTK)...", self)
        self.action_export_vtk.triggered.connect(self._on_export_vtk)
        file_menu.addAction(self.action_export_vtk)
        self.action_export_cfd_json = QAction("Export Mesh (JSON)...", self)
        self.action_export_cfd_json.triggered.connect(self._on_export_cfd_json)
        file_menu.addAction(self.action_export_cfd_json)
        file_menu.addSeparator()
        self.action_quit = QAction("Exit", self)
        self.action_quit.triggered.connect(self.close)
        file_menu.addAction(self.action_quit)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Tools", self)
        self.addToolBar(toolbar)

        self.action_select = QAction("Select", self)
        self._drawing_tool_actions = QActionGroup(self)
        self._drawing_tool_actions.setExclusive(True)
        self.action_select.setCheckable(True)
        self._drawing_tool_actions.addAction(self.action_select)
        self.action_select.setChecked(True)
        self.action_select.triggered.connect(lambda: self.canvas.set_tool(None))
        toolbar.addAction(self.action_select)

        self.action_line = QAction("Line", self)
        self.action_line.setCheckable(True)
        self._drawing_tool_actions.addAction(self.action_line)
        self.action_line.triggered.connect(lambda: self.canvas.set_tool(LineTool(self.canvas)))
        toolbar.addAction(self.action_line)

        self.action_arc = QAction("Arc", self)
        self.action_arc.setCheckable(True)
        self._drawing_tool_actions.addAction(self.action_arc)
        self.action_arc.triggered.connect(lambda: self.canvas.set_tool(ArcTool(self.canvas)))
        toolbar.addAction(self.action_arc)

        self.action_spline = QAction("Spline", self)
        self.action_spline.setCheckable(True)
        self._drawing_tool_actions.addAction(self.action_spline)
        self.action_spline.triggered.connect(lambda: self.canvas.set_tool(SplineTool(self.canvas)))
        toolbar.addAction(self.action_spline)

        self.action_split_edge = QAction("Split Edge", self)
        self.action_split_edge.setCheckable(True)
        self._drawing_tool_actions.addAction(self.action_split_edge)
        self.action_split_edge.triggered.connect(
            self.edges_panel.begin_split_by_click
        )
        toolbar.addAction(self.action_split_edge)

        self.action_insert_point = QAction("Insert Point", self)
        self.action_insert_point.triggered.connect(self._on_insert_point)
        toolbar.addAction(self.action_insert_point)

        toolbar.addSeparator()
        self.action_mesh = QAction("Generate Mesh", self)
        self.action_mesh.triggered.connect(self._on_generate_mesh)
        toolbar.addAction(self.action_mesh)

        self.action_clear_mesh = QAction("Clear Mesh", self)
        self.action_clear_mesh.triggered.connect(self.canvas.clear_mesh)
        toolbar.addAction(self.action_clear_mesh)

        toolbar.addSeparator()
        self.action_grid = QAction("Show Grid", self)
        self.action_grid.setCheckable(True)
        self.action_grid.setChecked(True)
        self.action_grid.triggered.connect(self._on_toggle_grid)
        toolbar.addAction(self.action_grid)

        toolbar.addWidget(QLabel(" Spacing: "))
        self.grid_spin = QDoubleSpinBox()
        self.grid_spin.setRange(0.1, 100.0)
        self.grid_spin.setValue(10.0)
        self.grid_spin.valueChanged.connect(self._on_grid_spacing_changed)
        toolbar.addWidget(self.grid_spin)

        toolbar.addSeparator()
        self.action_reset_zoom = QAction("Reset Zoom", self)
        self.action_reset_zoom.triggered.connect(self.canvas.reset_zoom)
        toolbar.addAction(self.action_reset_zoom)


        # --- live mesh controls ---
        toolbar.addSeparator()
        self.orthogonal_check = QCheckBox("Orthogonal")
        self.orthogonal_check.setToolTip("Enforces perpendicularity near the boundary")
        toolbar.addWidget(self.orthogonal_check)
        toolbar.addWidget(QLabel(" Layers: "))
        self.orthogonal_layers_spin = QSpinBox()
        self.orthogonal_layers_spin.setRange(1, 20)
        self.orthogonal_layers_spin.setMaximumWidth(58)
        toolbar.addWidget(self.orthogonal_layers_spin)
        toolbar.addWidget(QLabel(" Strength: "))
        self.orthogonal_strength_spin = QDoubleSpinBox()
        self.orthogonal_strength_spin.setRange(0.0, 1.0)
        self.orthogonal_strength_spin.setSingleStep(0.05)
        self.orthogonal_strength_spin.setDecimals(2)
        self.orthogonal_strength_spin.setMaximumWidth(72)
        toolbar.addWidget(self.orthogonal_strength_spin)
        toolbar.addWidget(QLabel(" Smoothing: "))
        self.smoothing_iterations_spin = QSpinBox()
        self.smoothing_iterations_spin.setRange(0, 2000)
        self.smoothing_iterations_spin.setSingleStep(5)
        self.smoothing_iterations_spin.setMaximumWidth(72)
        toolbar.addWidget(self.smoothing_iterations_spin)
        toolbar.addWidget(QLabel(" Relaxation: "))
        self.smoothing_relaxation_spin = QDoubleSpinBox()
        self.smoothing_relaxation_spin.setRange(0.05, 1.0)
        self.smoothing_relaxation_spin.setSingleStep(0.05)
        self.smoothing_relaxation_spin.setDecimals(2)
        self.smoothing_relaxation_spin.setMaximumWidth(72)
        toolbar.addWidget(self.smoothing_relaxation_spin)
        self.orthogonal_check.toggled.connect(self._schedule_live_mesh_update)
        for control in (self.orthogonal_layers_spin,
                        self.orthogonal_strength_spin,
                        self.smoothing_iterations_spin,
                        self.smoothing_relaxation_spin):
            control.valueChanged.connect(self._schedule_live_mesh_update)
        toolbar.addSeparator()
        self._decorate_toolbar(toolbar)

    def _on_canvas_tool_changed(self, tool) -> None:
        active_action = self.action_select
        if isinstance(tool, LineTool):
            active_action = self.action_line
        elif isinstance(tool, ArcTool):
            active_action = self.action_arc
        elif isinstance(tool, SplineTool):
            active_action = self.action_spline
        elif isinstance(tool, SplitEdgeTool):
            active_action = self.action_split_edge
        active_action.setChecked(True)

    # --- toolbar appearance ---
    def _cad_icon(self, kind: str) -> QIcon:
        """Create crisp CAD icons without relying on external files."""
        size = 28
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        blue = QColor("#2563EB")
        dark = QColor("#334155")
        accent = QColor("#F97316")
        pen = QPen(blue, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        if kind == "select":
            points = [(6, 4), (19, 16), (13, 17), (17, 24), (13, 26), (9, 19), (5, 23)]
            from PyQt5.QtCore import QPointF
            painter.drawPolygon(*[QPointF(x, y) for x, y in points])
        elif kind == "line":
            painter.drawLine(5, 22, 23, 6)
            painter.setBrush(accent)
            painter.drawEllipse(3, 20, 5, 5); painter.drawEllipse(20, 3, 5, 5)
        elif kind == "arc":
            painter.drawArc(4, 6, 20, 18, 10 * 16, 150 * 16)
            painter.setBrush(accent)
            painter.drawEllipse(4, 18, 5, 5); painter.drawEllipse(20, 17, 5, 5)
        elif kind == "spline":
            from PyQt5.QtGui import QPainterPath
            path = QPainterPath(); path.moveTo(3, 20)
            path.cubicTo(8, 2, 18, 26, 25, 7); painter.drawPath(path)
            painter.setBrush(accent)
            for x, y in ((3, 20), (10, 9), (18, 18), (25, 7)):
                painter.drawEllipse(x - 2, y - 2, 4, 4)
        elif kind == "point":
            painter.setPen(QPen(dark, 1.5)); painter.drawLine(14, 3, 14, 25)
            painter.drawLine(3, 14, 25, 14)
            painter.setPen(QPen(blue, 2)); painter.setBrush(accent)
            painter.drawEllipse(10, 10, 8, 8)
        elif kind == "mesh":
            painter.setPen(QPen(blue, 1.6))
            for n in (5, 11, 17, 23):
                painter.drawLine(n, 4, n, 24); painter.drawLine(4, n, 24, n)
        elif kind == "clear_mesh":
            painter.setPen(QPen(blue, 1.2))
            for n in (6, 11, 16, 21):
                painter.drawLine(n, 5, n, 23); painter.drawLine(5, n, 23, n)
            painter.setPen(QPen(QColor("#DC2626"), 3, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(6, 6, 22, 22); painter.drawLine(22, 6, 6, 22)
        elif kind == "grid":
            painter.setPen(QPen(dark, 1.4))
            for n in (6, 11, 16, 21):
                painter.drawLine(n, 4, n, 24); painter.drawLine(4, n, 24, n)
        elif kind == "zoom":
            painter.setPen(QPen(blue, 2.2)); painter.drawEllipse(4, 4, 15, 15)
            painter.drawLine(17, 17, 25, 25)
            painter.setPen(QPen(accent, 1.8)); painter.drawLine(8, 11, 15, 11)
            painter.drawLine(11, 8, 11, 15)
        painter.end()
        return QIcon(pixmap)

    def _decorate_toolbar(self, toolbar: QToolBar) -> None:
        """Apply icons, visual shortcuts, and tooltips to the toolbar."""
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(True)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.setStyleSheet(
            "QToolBar { spacing: 4px; padding: 4px; background: #F8FAFC; "
            "border-bottom: 1px solid #CBD5E1; }"
            "QToolButton { padding: 4px 7px; border-radius: 5px; }"
            "QToolButton:hover { background: #DBEAFE; }"
            "QToolButton:pressed { background: #BFDBFE; }"
            "QToolButton:checked { background: #BFDBFE; border: 1px solid #2563EB; }"
        )

        entries = (
            (self.action_select, "select", "Select and edit geometry", "Select edges or drag vertices and control points."),
            (self.action_line, "line", "Draw a line", "Create a segment with two clicks: start and end."),
            (self.action_arc, "arc", "Draw a circular arc", "Create an arc with three clicks: center, start, and end."),
            (self.action_spline, "spline", "Draw a spline", "Add points with left-click and finish with right-click."),
            (self.action_insert_point, "point", "Insert point by coordinates", "Insert a vertex by entering its X and Y coordinates."),
            (self.action_mesh, "mesh", "Generate Mesh", "Generate or update the structured mesh for all blocks."),
            (self.action_clear_mesh, "clear_mesh", "Hide mesh", "Remove the mesh from the canvas without deleting CAD geometry."),
            (self.action_grid, "grid", "Show or hide grid", "Show or hide the canvas reference grid."),
            (self.action_reset_zoom, "zoom", "Fit all", "Center and fit all geometry in the visible area."),
        )
        for action, icon_name, status_tip, tool_tip in entries:
            action.setIcon(self._cad_icon(icon_name))
            action.setToolTip(tool_tip)
            action.setStatusTip(status_tip)

        self.orthogonal_check.setToolTip(
            "Make interior lines perpendicular to the boundary."
        )
        self.orthogonal_layers_spin.setToolTip(
            "Number of inner layers affected by orthogonalization."
        )
        self.orthogonal_strength_spin.setToolTip(
            "Orthogonal correction strength: 0 leaves unchanged; 1 applies the maximum."
        )
        self.smoothing_iterations_spin.setToolTip(
            "Number of elliptic mesh-smoothing iterations."
        )
        self.smoothing_relaxation_spin.setToolTip(
            "Smoothing relaxation factor; lower values produce gentler changes."
        )
        self.grid_spin.setToolTip("Spacing between canvas grid lines.")

    def _on_insert_point(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Insert Point")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        spin_x = QDoubleSpinBox()
        spin_x.setRange(-999999, 999999)
        spin_x.setDecimals(4)
        spin_x.setValue(0)
        spin_y = QDoubleSpinBox()
        spin_y.setRange(-999999, 999999)
        spin_y.setDecimals(4)
        spin_y.setValue(0)
        form.addRow("X:", spin_x)
        form.addRow("Y:", spin_y)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            self.document.add_vertex(Point2D(spin_x.value(), spin_y.value()))

    def _on_toggle_grid(self, checked: bool) -> None:
        self.canvas.show_grid = checked
        self.canvas.viewport().update()

    def _on_grid_spacing_changed(self, value: float) -> None:
        self.canvas.grid_spacing = value
        self.canvas.viewport().update()

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self.coords_label.setText("X: {:.2f}, Y: {:.2f}".format(x, y))

    def _on_new(self) -> None:
        self.document.load_from(Document())
        self.current_path = None
        self.canvas.clear_mesh()
        self.canvas.clear_highlight()
        self._update_title()
        self.status_label.setText("New project.")

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "MeshCAD (*.json);;All Files (*)")
        if not path: return
        try:
            data = load_project(path)
            loaded = Document.from_dict(data)
        except Exception as e:
            QMessageBox.critical(self, "Open Error", str(e))
            return
        self.document.load_from(loaded)
        self.current_path = Path(path)
        self.canvas.clear_mesh()
        self._update_title()
        self.status_label.setText("Project loaded: {}".format(path))

    def _on_import_point_sequence(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Point Sequence",
            "",
            "Point Sequences (*.csv *.txt);;All Files (*)",
        )
        if not path:
            return
        try:
            points = load_point_sequence(Path(path))
        except (OSError, UnicodeError, ValueError, csv.Error) as error:
            QMessageBox.critical(self, "Point Import Error", str(error))
            return

        preview = ImportPointSequenceDialog(points, self)
        if preview.exec_() != QDialog.Accepted:
            return
        try:
            edge = self.document.add_point_sequence(points)
        except ValueError as error:
            QMessageBox.critical(self, "Point Import Error", str(error))
            return
        self.canvas.set_tool(None)
        self.canvas.reset_zoom()
        self.status_label.setText(
            "Imported {} points as edge {}.".format(len(points), edge.id)
        )

    def _on_save(self) -> None:
        if self.current_path is None: self._on_save_as()
        else: self._save_to(self.current_path)

    def _on_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save As", "project.json", "MeshCAD (*.json);;All Files (*)")
        if path: self._save_to(Path(path))

    def _save_to(self, path: Path) -> None:
        try:
            save_project(self.document.to_dict(), path)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))
            return
        self.current_path = path
        self._update_title()
        self.status_label.setText("Saved to: {}".format(path))

    def _on_export_vtk(self) -> None:
        if not self.document.block_meshes:
            QMessageBox.information(self, "No Mesh", "Generate the mesh first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export VTK", "mesh.pvd", "ParaView (*.pvd);;All Files (*)")
        if not path: return
        try:
            from meshcad.io.vtk_io import export_mesh_vtk
            export_mesh_vtk(self.document.block_meshes, path)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
            return
        self.status_label.setText("Mesh exported to: {}".format(path))

    def _on_export_cfd_json(self) -> None:
        if not self.document.blocks:
            QMessageBox.information(
                self, "No CFD Mesh", "Define at least one block before exporting."
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Mesh",
            "mesh.cfd.json",
            "MeshCAD CFD Mesh (*.json);;All Files (*)",
        )
        if not path:
            return
        output = Path(path)
        if output.suffix.lower() != ".json":
            output = Path(str(output) + ".json")
        try:
            block_meshes, errors = self.document.generate_mesh()
            if errors:
                raise ValueError("Mesh generation failed:\n" + "\n".join(errors))
            if len(block_meshes) != len(self.document.blocks):
                raise ValueError("Not all blocks produced a mesh")
            cfd_mesh = build_cfd_mesh(
                block_meshes,
                self.document.blocks,
                self.document.topology,
                self.document.mesh,
                self.document.patches,
            )
            write_cfd_mesh_json(
                output, cfd_mesh, self.document.patches, pretty=False
            )
        except Exception as error:
            QMessageBox.critical(self, "CFD Export Error", str(error))
            return
        self.status_label.setText("Mesh exported to: {}".format(output))

    def _update_title(self) -> None:
        if self.current_path is None: self.setWindowTitle("MeshCAD - untitled")
        else: self.setWindowTitle("MeshCAD - {}".format(self.current_path))

    def _on_project_replaced(self) -> None:
        self._mesh_update_timer.stop()
        self.edges_panel.refresh()
        self._sync_mesh_controls_from_document()

    def _schedule_live_mesh_update(self, *args) -> None:
        """Debounce rapid changes so the mesh is regenerated only once."""
        if not self._updating_mesh_controls:
            self._mesh_update_timer.start()

    def _apply_live_mesh_options(self) -> None:
        """Update options and regenerate the mesh without an Apply button."""
        def apply_options() -> None:
            self.document.mesh_improvement = SmoothingOptions(
                orthogonal=self.orthogonal_check.isChecked(),
                orthogonal_layers=self.orthogonal_layers_spin.value(),
                smoothing_iterations=self.smoothing_iterations_spin.value(),
                relaxation=self.smoothing_relaxation_spin.value(),
                orthogonal_strength=self.orthogonal_strength_spin.value(),
            )
            if self.document.blocks:
                self._on_generate_mesh()
            else:
                self.status_label.setText("Parameters updated; no blocks exist yet.")

        self.document.perform_undoable("Change mesh options", apply_options)

    def _sync_mesh_controls_from_document(self) -> None:
        """Load current project parameters into the toolbar."""
        self._updating_mesh_controls = True
        try:
            options = self.document.mesh_improvement
            self.orthogonal_check.setChecked(options.orthogonal)
            self.orthogonal_layers_spin.setValue(options.orthogonal_layers)
            self.orthogonal_strength_spin.setValue(options.orthogonal_strength)
            self.smoothing_iterations_spin.setValue(options.smoothing_iterations)
            self.smoothing_relaxation_spin.setValue(options.relaxation)
        finally:
            self._updating_mesh_controls = False

    def _on_generate_mesh(self) -> None:
        meshes, errors = self.document.generate_mesh()
        if errors:
            self.status_label.setText("Errors: " + "; ".join(errors))
        else:
            total_cells = sum(bm.cell_count() for bm in meshes)
            self.status_label.setText("Mesh generated: {} blocks, {} cells".format(len(meshes), total_cells))


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
