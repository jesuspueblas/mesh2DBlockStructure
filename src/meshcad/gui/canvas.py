"""Interactive CAD canvas based on QGraphicsView."""

from __future__ import annotations
import math
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsScene, QGraphicsView,
    QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox, QDialogButtonBox
)
from meshcad.core.geometry.point import Point2D
from meshcad.gui.document import Document
from meshcad.gui.items import GeometryItem

VERTEX_RADIUS = 4.0
GRIP_RADIUS = 3.5
SNAP_TOLERANCE = 8.0


class CadCanvas(QGraphicsView):
    mouse_moved = pyqtSignal(float, float)
    edge_clicked = pyqtSignal(int)

    def __init__(self, document: Document, parent=None) -> None:
        super().__init__(parent)
        self.document = document
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setMouseTracking(True)
        self.setBackgroundBrush(QBrush(QColor(250, 250, 252)))

        self.scale(1, -1)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.tool = None
        self._drag_target = None
        self._is_panning = False
        self._last_mouse_pos = None

        self._preview_item = None
        self._highlight_item = None
        self._mesh_item = None
        self._boundary_items = []

        self.show_grid = True
        self.grid_spacing = 10.0

        self._vertex_items = {}
        self._grip_items = []
        self._geometry_items = []

        self.document.topology_changed.connect(self._redraw_all)
        self.document.mesh_generated.connect(self._on_mesh_generated)
        self.document.patches_changed.connect(self.refresh_boundary_overlay)
        self.document.blocks_changed.connect(self.refresh_boundary_overlay)

    def _model_bounding_rect(self):
        """Calculate the bounds of the complete model and visible mesh."""
        from PyQt5.QtCore import QRectF
        bounds = None

        def include(x0, y0, x1, y1):
            nonlocal bounds
            rect = QRectF(min(x0, x1), min(y0, y1),
                          abs(x1 - x0), abs(y1 - y0))
            bounds = rect if bounds is None else bounds.united(rect)

        for edge in self.document.topology.edges():
            lo, hi = edge.geometry.bounding_box()
            include(lo.x, lo.y, hi.x, hi.y)
        for vertex in self.document.topology.vertices():
            include(vertex.point.x, vertex.point.y,
                    vertex.point.x, vertex.point.y)
        for block_mesh in self.document.block_meshes:
            for row in block_mesh.grid:
                for point in row:
                    include(point.x, point.y, point.x, point.y)
        return bounds

    def reset_zoom(self) -> None:
        """Fit the entire model, reset panning, and keep Y pointing upward."""
        rect = self._model_bounding_rect()
        self.resetTransform()
        self.scale(1.0, -1.0)
        if rect is None:
            self.centerOn(0.0, 0.0)
            self.viewport().update()
            return
        if rect.width() < 1.0:
            rect.adjust(-0.5, 0.0, 0.5, 0.0)
        if rect.height() < 1.0:
            rect.adjust(0.0, -0.5, 0.0, 0.5)
        margin = max(10.0, 0.05 * max(rect.width(), rect.height()))
        rect.adjust(-margin, -margin, margin, margin)
        self.scene().setSceneRect(rect)
        self.fitInView(rect, Qt.KeepAspectRatio)
        self.centerOn(rect.center())
        self.viewport().update()

    def set_tool(self, tool) -> None:
        if self.tool is not None:
            self.tool.cancel()
        self.tool = tool

    def add_geometry(self, geometry):
        topo = self.document.topology
        v_start = topo.find_vertex_at(geometry.start_point()) or topo.add_vertex(geometry.start_point())
        v_end = topo.find_vertex_at(geometry.end_point()) or topo.add_vertex(geometry.end_point())
        edge = topo.add_edge(v_start, v_end, geometry)
        self.document.notify_change()
        return edge

    def snap_to_vertex(self, scene_point: Point2D):
        topo = self.document.topology
        best = None
        best_dist = None
        for v in topo.vertices():
            d = v.point.distance_to(scene_point)
            if best_dist is None or d < best_dist:
                best = v
                best_dist = d
        if best is None:
            return None
        scale = self.transform().m11()
        if scale <= 0:
            return best
        tol_scene = SNAP_TOLERANCE / scale
        if best_dist is not None and best_dist <= tol_scene:
            return best
        return None

    def show_preview(self, geometry) -> None:
        self.clear_preview()
        if geometry is None:
            return
        item = GeometryItem(geometry, preview=True)
        self.scene().addItem(item)
        self._preview_item = item

    def clear_preview(self) -> None:
        if self._preview_item is not None:
            self.scene().removeItem(self._preview_item)
            self._preview_item = None

    def highlight_loop(self, loop) -> None:
        self.clear_highlight()
        topo = self.document.topology
        path = QPainterPath()
        started = False
        for oe in loop:
            geom = topo.get_edge(oe.edge_id).geometry
            pts = geom.sample(30)
            if oe.reversed:
                pts = list(reversed(pts))
            for p in pts:
                if not started:
                    path.moveTo(p.x, p.y)
                    started = True
                else:
                    path.lineTo(p.x, p.y)

        item = QGraphicsPathItem(path)
        pen = QPen(QColor(60, 180, 60))
        pen.setWidthF(4.0)
        pen.setCosmetic(True)
        item.setPen(pen)
        item.setZValue(8.0)
        self.scene().addItem(item)
        self._highlight_item = item

    def highlight_edges(self, edge_ids: list) -> None:
        self.clear_highlight()
        if not edge_ids:
            return
        path = QPainterPath()
        topo = self.document.topology
        for eid in edge_ids:
            geom = topo.get_edge(eid).geometry
            pts = geom.sample(30)
            path.moveTo(pts[0].x, pts[0].y)
            for p in pts[1:]:
                path.lineTo(p.x, p.y)

        item = QGraphicsPathItem(path)
        pen = QPen(QColor(240, 140, 20))
        pen.setWidthF(3.0)
        pen.setCosmetic(True)
        item.setPen(pen)
        item.setZValue(8.0)
        self.scene().addItem(item)
        self._highlight_item = item

    def clear_highlight(self) -> None:
        if self._highlight_item is not None:
            self.scene().removeItem(self._highlight_item)
            self._highlight_item = None


    def clear_boundary_overlay(self) -> None:
        for item in self._boundary_items:
            self.scene().removeItem(item)
        self._boundary_items = []

    def refresh_boundary_overlay(self) -> None:
        """Draw boundary classification without changing CAD item styling."""
        from meshcad.core.topology.usage import find_edge_uses

        self.clear_boundary_overlay()
        usage = find_edge_uses(self.document.blocks)
        for edge_id, uses in usage.items():
            if len(uses) == 1:
                patch = self.document.patches.patch_for_edge(edge_id)
                color = QColor(240, 145, 25) if patch is None else QColor.fromHsv((patch.id * 67) % 360, 150, 210)
                width = 4.0
                style = Qt.SolidLine
            elif len(uses) == 2:
                color = QColor(70, 165, 105)
                width = 2.5
                style = Qt.DashLine
            else:
                color = QColor(220, 30, 150)
                width = 4.0
                style = Qt.DashDotLine
            try:
                geometry = self.document.topology.get_edge(edge_id).geometry
            except (KeyError, ValueError):
                continue
            item = GeometryItem(geometry)
            item.setFlag(QGraphicsPathItem.ItemIsSelectable, False)
            pen = QPen(color)
            pen.setWidthF(width)
            pen.setCosmetic(True)
            pen.setStyle(style)
            item.setPen(pen)
            item.setZValue(6.0)
            self.scene().addItem(item)
            self._boundary_items.append(item)

    def flash_vertex(self, vertex_id: int) -> None:
        item = self._vertex_items.get(vertex_id)
        if item is None:
            return
        original_brush = item.brush()
        item.setBrush(QBrush(QColor(60, 200, 60)))
        QTimer.singleShot(200, lambda: item.setBrush(original_brush))

    def show_mesh(self, block_meshes) -> None:
        self.clear_mesh()
        path = QPainterPath()
        for bm in block_meshes:
            grid = bm.grid
            n_v = len(grid)
            if n_v == 0: continue
            n_u = len(grid[0])

            for i in range(n_u):
                path.moveTo(grid[0][i].x, grid[0][i].y)
                for j in range(1, n_v):
                    path.lineTo(grid[j][i].x, grid[j][i].y)
            for j in range(n_v):
                path.moveTo(grid[j][0].x, grid[j][0].y)
                for i in range(1, n_u):
                    path.lineTo(grid[j][i].x, grid[j][i].y)

        item = QGraphicsPathItem(path)
        pen = QPen(QColor(40, 40, 40))
        pen.setWidthF(0.8)
        pen.setCosmetic(True)
        item.setPen(pen)
        item.setZValue(3.0)
        self.scene().addItem(item)
        self._mesh_item = item

    def clear_mesh(self) -> None:
        if self._mesh_item is not None:
            self.scene().removeItem(self._mesh_item)
            self._mesh_item = None

    def _on_mesh_generated(self) -> None:
        self.show_mesh(self.document.block_meshes)

    def wheelEvent(self, event) -> None:
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if self.tool is not None:
            self.tool.mouse_press(event)
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos())
            p = Point2D(pos.x(), pos.y())

            v = self.snap_to_vertex(p)
            if v is not None:
                self._drag_target = ('vertex', v.id)
                event.accept()
                return

            scale = self.transform().m11()
            tol = SNAP_TOLERANCE / scale if scale > 0 else SNAP_TOLERANCE
            for edge in self.document.topology.edges():
                for i, g in enumerate(edge.geometry.get_grips()):
                    if g.distance_to(p) <= tol:
                        self._drag_target = ('grip', edge.id, i)
                        event.accept()
                        return

            # Detect clicks on edges.
            items = self.items(event.pos())
            for item in items:
                if isinstance(item, GeometryItem) and hasattr(item, 'edge_id'):
                    self.edge_clicked.emit(item.edge_id)
                    event.accept()
                    return

            self.clear_highlight()
            self.edge_clicked.emit(-1)

        super().mousePressEvent(event)

    def _grip_near(self, point: Point2D):
        """Return (edge_id, grip_index, grip) if a grip is under the cursor."""
        scale = abs(self.transform().m11())
        tolerance = SNAP_TOLERANCE / scale if scale > 0 else SNAP_TOLERANCE
        best = None
        best_distance = None
        for edge in self.document.topology.edges():
            for grip_index, grip in enumerate(edge.geometry.get_grips()):
                distance = grip.distance_to(point)
                if distance <= tolerance and (best_distance is None or distance < best_distance):
                    best = (edge.id, grip_index, grip)
                    best_distance = distance
        return best

    def _edit_point_dialog(self, title: str, point: Point2D):
        """Request X/Y coordinates and return a Point2D, or None if canceled."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        spin_x = QDoubleSpinBox()
        spin_x.setRange(-999999, 999999)
        spin_x.setDecimals(6)
        spin_x.setValue(point.x)
        spin_y = QDoubleSpinBox()
        spin_y.setRange(-999999, 999999)
        spin_y.setDecimals(6)
        spin_y.setValue(point.y)
        form.addRow("X:", spin_x)
        form.addRow("Y:", spin_y)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec_() != QDialog.Accepted:
            return None
        return Point2D(spin_x.value(), spin_y.value())

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.tool is None:
            scene_pos = self.mapToScene(event.pos())
            point = Point2D(scene_pos.x(), scene_pos.y())

            # Topological vertices take priority when they overlap a grip.
            vertex = self.snap_to_vertex(point)
            if vertex is not None:
                new_point = self._edit_point_dialog("Edit Vertex", vertex.point)
                if new_point is not None:
                    self.document.topology.move_vertex(vertex.id, new_point)
                    self.document.notify_change()
                event.accept()
                return

            grip_hit = self._grip_near(point)
            if grip_hit is not None:
                edge_id, grip_index, grip = grip_hit
                new_point = self._edit_point_dialog("Edit Control Point", grip)
                if new_point is not None:
                    self.document.topology.move_edge_grip(edge_id, grip_index, new_point)
                    self.document.notify_change()
                event.accept()
                return

        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._is_panning:
            delta = event.pos() - self._last_mouse_pos
            self._last_mouse_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        pos = self.mapToScene(event.pos())
        self.mouse_moved.emit(pos.x(), pos.y())

        if self._drag_target:
            p = Point2D(pos.x(), pos.y())
            if self._drag_target[0] == 'vertex':
                self.document.topology.move_vertex(self._drag_target[1], p)
            else:
                self.document.topology.move_edge_grip(self._drag_target[1], self._drag_target[2], p)
            self.document.notify_change()
            event.accept()
            return

        if self.tool is not None:
            self.tool.mouse_move(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return

        if self._drag_target:
            self._drag_target = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape and self.tool is not None:
            self.tool.cancel()
            self.tool = None
            event.accept()
            return
        super().keyPressEvent(event)

    def drawBackground(self, painter: QPainter, rect) -> None:
        super().drawBackground(painter, rect)
        if not self.show_grid or self.grid_spacing <= 0:
            return

        grid_size = self.grid_spacing
        min_x = math.floor(rect.left() / grid_size) * grid_size
        max_x = math.ceil(rect.right() / grid_size) * grid_size
        min_y = math.floor(min(rect.top(), rect.bottom()) / grid_size) * grid_size
        max_y = math.ceil(max(rect.top(), rect.bottom()) / grid_size) * grid_size

        pen = QPen(QColor(230, 230, 235))
        pen.setWidthF(0.5)
        painter.setPen(pen)

        x = min_x
        while x <= max_x:
            painter.drawLine(int(x), int(min_y), int(x), int(max_y))
            x += grid_size

        y = min_y
        while y <= max_y:
            painter.drawLine(int(min_x), int(y), int(max_x), int(y))
            y += grid_size

    def _redraw_all(self) -> None:
        for item in self._geometry_items: self.scene().removeItem(item)
        self._geometry_items.clear()
        for item in self._vertex_items.values(): self.scene().removeItem(item)
        self._vertex_items.clear()
        for item in self._grip_items: self.scene().removeItem(item)
        self._grip_items.clear()

        for edge in self.document.topology.edges():
            item = GeometryItem(edge.geometry)
            item.edge_id = edge.id
            self.scene().addItem(item)
            self._geometry_items.append(item)

        self.refresh_boundary_overlay()

        pen_v = QPen(QColor(200, 40, 40))
        brush_v = QBrush(QColor(255, 220, 220))
        for v in self.document.topology.vertices():
            item = QGraphicsEllipseItem(v.point.x - VERTEX_RADIUS, v.point.y - VERTEX_RADIUS,
                                        VERTEX_RADIUS * 2, VERTEX_RADIUS * 2)
            item.setPen(pen_v)
            item.setBrush(brush_v)
            item.setZValue(10.0)
            self.scene().addItem(item)
            self._vertex_items[v.id] = item

        pen_g = QPen(QColor(40, 100, 200))
        brush_g = QBrush(QColor(200, 220, 255))
        for edge in self.document.topology.edges():
            for g in edge.geometry.get_grips():
                item = QGraphicsEllipseItem(g.x - GRIP_RADIUS, g.y - GRIP_RADIUS,
                                            GRIP_RADIUS * 2, GRIP_RADIUS * 2)
                item.setPen(pen_g)
                item.setBrush(brush_g)
                item.setZValue(9.0)
                self.scene().addItem(item)
                self._grip_items.append(item)
