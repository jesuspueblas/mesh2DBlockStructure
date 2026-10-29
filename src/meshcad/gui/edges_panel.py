"""Panel for editing the mesh specification of each edge."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFormLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.distribution import BiasedDistribution, UniformDistribution
from meshcad.core.mesh.model import EdgeMeshSpec
from meshcad.gui.action_icons import configure_button
from meshcad.gui.document import Document
from meshcad.gui.tools.split_edge_tool import SplitEdgeTool


class EdgesPanel(QDockWidget):
    def __init__(self, document: Document, canvas, parent=None) -> None:
        super().__init__("Distributions", parent)
        self.document = document
        self.canvas = canvas

        container = QWidget()
        layout = QVBoxLayout(container)

        self.refresh_button = QPushButton("Refresh Edges")
        configure_button(
            self.refresh_button, "refresh", "Refresh the edge list."
        )
        self.refresh_button.clicked.connect(self.refresh)
        layout.addWidget(self.refresh_button)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

        form = QFormLayout()
        self.nodes_spin = QSpinBox()
        self.nodes_spin.setRange(2, 10000)
        self.nodes_spin.setValue(5)
        form.addRow("Nodes:", self.nodes_spin)

        self.dist_combo = QComboBox()
        self.dist_combo.addItems(["Uniform", "Biased"])
        self.dist_combo.currentIndexChanged.connect(self._on_dist_changed)
        form.addRow("Distribution:", self.dist_combo)

        self.bias_spin = QDoubleSpinBox()
        self.bias_spin.setRange(0.01, 100.0)
        self.bias_spin.setValue(2.0)
        self.bias_spin.setSingleStep(0.1)
        self.bias_spin.setEnabled(False)
        form.addRow("Bias:", self.bias_spin)
        layout.addLayout(form)

        self.apply_button = QPushButton("Apply to Selected")
        configure_button(
            self.apply_button, "apply", "Apply these settings to selected edges."
        )
        self.apply_button.clicked.connect(self._on_apply)
        layout.addWidget(self.apply_button)

        self.delete_button = QPushButton("Delete Selected Edge(s)")
        configure_button(
            self.delete_button, "delete", "Delete selected edges not used by a block."
        )
        self.delete_button.clicked.connect(self._on_delete)
        layout.addWidget(self.delete_button)

        self.split_button = QPushButton("Split Selected Edge by Clicking")
        configure_button(
            self.split_button, "split_click", "Split the selected edge by clicking on it."
        )
        self.split_button.clicked.connect(self._on_split_by_click)
        layout.addWidget(self.split_button)

        self.split_coordinates_button = QPushButton("Split Selected Edge at Coordinates...")
        configure_button(
            self.split_coordinates_button,
            "split_coordinates",
            "Split the selected edge at entered X and Y coordinates.",
        )
        self.split_coordinates_button.clicked.connect(self._on_split_at_coordinates)
        layout.addWidget(self.split_coordinates_button)

        self.status = QLabel("Refresh to display edges.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.setWidget(container)

    def select_edges(self, edge_ids: list, toggle: bool = False) -> None:
        self.list_widget.blockSignals(True)
        if not toggle:
            self.list_widget.clearSelection()
        edges = self.document.topology.edges()

        for item_idx in range(self.list_widget.count()):
            item = self.list_widget.item(item_idx)
            if 0 <= item_idx < len(edges) and edges[item_idx].id in edge_ids:
                item.setSelected(not item.isSelected() if toggle else True)

        self.list_widget.blockSignals(False)
        self._on_selection_changed()

    def refresh(self) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for edge in self.document.topology.edges():
            spec = self.document.mesh.get_spec(edge.id)
            label = "Edge {}: v{}->v{}, {} nodes, {}".format(
                edge.id, edge.start_vertex_id, edge.end_vertex_id, spec.n_nodes, self._dist_name(spec.distribution)
            )
            self.list_widget.addItem(QListWidgetItem(label))
        self.list_widget.blockSignals(False)

        if self.list_widget.count() == 0:
            self.status.setText("No edges yet.")
        else:
            self.status.setText("{} edges. Select one or more.".format(self.list_widget.count()))

    def selected_edge_ids(self) -> list:
        edges = self.document.topology.edges()
        result = []
        for item in self.list_widget.selectedItems():
            row = self.list_widget.row(item)
            if 0 <= row < len(edges):
                result.append(edges[row].id)
        return result

    def _on_selection_changed(self) -> None:
        selected_items = self.list_widget.selectedItems()
        edge_ids = []
        edges = self.document.topology.edges()

        for item in selected_items:
            row = self.list_widget.row(item)
            if 0 <= row < len(edges):
                edge_ids.append(edges[row].id)

        self.canvas.highlight_edges(edge_ids)

        if len(selected_items) == 1:
            row = self.list_widget.row(selected_items[0])
            spec = self.document.mesh.get_spec(edges[row].id)
            self.nodes_spin.setValue(spec.n_nodes)
            if isinstance(spec.distribution, BiasedDistribution):
                self.dist_combo.setCurrentText("Biased")
                self.bias_spin.setValue(spec.distribution.bias)
                self.bias_spin.setEnabled(True)
            else:
                self.dist_combo.setCurrentText("Uniform")
                self.bias_spin.setEnabled(False)

    def _on_dist_changed(self, index: int) -> None:
        self.bias_spin.setEnabled(index == 1)

    def _on_apply(self) -> None:
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            self.status.setText("Select at least one edge first.")
            return

        edges = self.document.topology.edges()
        specs = []
        for item in selected_items:
            row = self.list_widget.row(item)
            if 0 <= row < len(edges):
                edge = edges[row]
                if self.dist_combo.currentText() == "Biased":
                    dist = BiasedDistribution(bias=self.bias_spin.value())
                else:
                    dist = UniformDistribution()
                specs.append(EdgeMeshSpec(edge.id, self.nodes_spin.value(), dist))

        try:
            self.document.set_edge_specs(specs)
        except ValueError as error:
            self.status.setText("Could not update edge distributions: {}".format(error))
            return
        self.refresh()
        self.status.setText("{} edges updated.".format(len(specs)))

    def _on_delete(self) -> None:
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return

        edges = self.document.topology.edges()
        edge_ids_to_delete = []
        for item in selected_items:
            row = self.list_widget.row(item)
            if 0 <= row < len(edges):
                edge_ids_to_delete.append(edges[row].id)

        self.canvas.clear_highlight()

        success, fail = self.document.remove_edges(edge_ids_to_delete)
        self.refresh()

        if fail > 0:
            self.status.setText("{} edges deleted. {} could not be deleted because they belong to a block.".format(success, fail))
        else:
            self.status.setText("{} edges deleted.".format(success))

    def _selected_edge_for_split(self):
        edge_ids = self.selected_edge_ids()
        if len(edge_ids) != 1:
            self.status.setText("Select exactly one edge to split.")
            return None
        return self.document.topology.get_edge(edge_ids[0])

    def begin_split_by_click(self) -> None:
        edge = self._selected_edge_for_split()
        if edge is None:
            self.canvas.set_tool(None)
            return
        self.canvas.set_tool(
            SplitEdgeTool(
                self.canvas,
                edge.id,
                self._on_split_complete,
                self._on_split_error,
            )
        )
        self.status.setText("Click on the selected edge where it should be split.")

    def _on_split_by_click(self) -> None:
        self.begin_split_by_click()

    def _on_split_at_coordinates(self) -> None:
        edge = self._selected_edge_for_split()
        if edge is None:
            return
        midpoint = edge.geometry.evaluate(0.5)
        x, accepted = QInputDialog.getDouble(
            self, "Split Edge", "X:", midpoint.x, -999999999, 999999999, 8
        )
        if not accepted:
            return
        y, accepted = QInputDialog.getDouble(
            self, "Split Edge", "Y:", midpoint.y, -999999999, 999999999, 8
        )
        if not accepted:
            return

        tolerance = max(1e-8, edge.geometry.length() * 1e-7)
        try:
            edges = self.document.split_edge_at_point(
                edge.id, Point2D(x, y), tolerance=tolerance
            )
        except (KeyError, TypeError, ValueError) as error:
            self._on_split_error(str(error))
            return
        self._on_split_complete(edges)

    def _on_split_complete(self, edges) -> None:
        self.refresh()
        self.select_edges([edge.id for edge in edges])
        self.status.setText(
            "Edge split into edges {} and {}.".format(
                edges[0].id, edges[1].id
            )
        )

    def _on_split_error(self, message) -> None:
        self.status.setText("Could not split edge: {}".format(message))

    @staticmethod
    def _dist_name(dist):
        if isinstance(dist, BiasedDistribution):
            return "biased({:g})".format(dist.bias)
        return "uniform"
