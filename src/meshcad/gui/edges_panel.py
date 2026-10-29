"""Panel for editing the mesh specification of each edge."""

from __future__ import annotations
from PyQt5.QtWidgets import (
    QComboBox, QDockWidget, QDoubleSpinBox, QFormLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout, QWidget, QAbstractItemView
)
from meshcad.core.mesh.distribution import BiasedDistribution, UniformDistribution
from meshcad.core.mesh.model import EdgeMeshSpec
from meshcad.gui.document import Document


class EdgesPanel(QDockWidget):
    def __init__(self, document: Document, canvas, parent=None) -> None:
        super().__init__("Distributions", parent)
        self.document = document
        self.canvas = canvas

        container = QWidget()
        layout = QVBoxLayout(container)

        self.refresh_button = QPushButton("Refresh Edges")
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
        self.apply_button.clicked.connect(self._on_apply)
        layout.addWidget(self.apply_button)

        self.delete_button = QPushButton("Delete Selected Edge(s)")
        self.delete_button.clicked.connect(self._on_delete)
        layout.addWidget(self.delete_button)

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

        self.document.set_edge_specs(specs)
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

    @staticmethod
    def _dist_name(dist):
        if isinstance(dist, BiasedDistribution):
            return "biased({:g})".format(dist.bias)
        return "uniform"
