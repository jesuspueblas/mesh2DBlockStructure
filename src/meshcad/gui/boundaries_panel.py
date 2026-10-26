"""Dock widget for creating and assigning CFD boundary patches."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QDoubleSpinBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QDockWidget,
)

from meshcad.core.boundary import BoundaryType, PeriodicTransform
from meshcad.core.topology.usage import find_edge_uses
from meshcad.gui.document import Document

PATCH_ID_ROLE = Qt.UserRole
PAIR_ID_ROLE = Qt.UserRole


class BoundaryPatchDialog(QDialog):
    def __init__(self, parent=None, name: str = "", boundary_type=BoundaryType.WALL):
        super().__init__(parent)
        self.setWindowTitle("Boundary patch")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(name)
        self.type_combo = QComboBox()
        for item in BoundaryType:
            self.type_combo.addItem(item.value.capitalize(), item.value)
        self.type_combo.setCurrentIndex(max(0, self.type_combo.findData(BoundaryType(boundary_type).value)))
        layout.addRow("Name", self.name_edit)
        layout.addRow("Type", self.type_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self):
        return self.name_edit.text(), BoundaryType(self.type_combo.currentData())


class PeriodicPairDialog(QDialog):
    """Collect an explicit translational periodic-pair definition."""

    def __init__(self, periodic_patches, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Periodic pair")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.source_combo = QComboBox()
        self.target_combo = QComboBox()
        for patch in periodic_patches:
            self.source_combo.addItem(patch.name, patch.id)
            self.target_combo.addItem(patch.name, patch.id)
        if self.target_combo.count() > 1:
            self.target_combo.setCurrentIndex(1)
        self.reversed_check = QCheckBox("Reverse target node order")
        self.dx_spin = self._coordinate_spin()
        self.dy_spin = self._coordinate_spin()
        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setDecimals(12)
        self.tolerance_spin.setRange(1.0e-12, 1.0e6)
        self.tolerance_spin.setValue(1.0e-8)
        self.tolerance_spin.setSingleStep(1.0e-8)
        layout.addRow("Name", self.name_edit)
        layout.addRow("Source patch", self.source_combo)
        layout.addRow("Target patch", self.target_combo)
        layout.addRow("Orientation", self.reversed_check)
        layout.addRow("Translation X", self.dx_spin)
        layout.addRow("Translation Y", self.dy_spin)
        layout.addRow("Tolerance", self.tolerance_spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @staticmethod
    def _coordinate_spin():
        spin = QDoubleSpinBox()
        spin.setDecimals(12)
        spin.setRange(-1.0e12, 1.0e12)
        return spin

    def values(self):
        return {
            "name": self.name_edit.text(),
            "source_patch_id": int(self.source_combo.currentData()),
            "target_patch_id": int(self.target_combo.currentData()),
            "reversed": self.reversed_check.isChecked(),
            "tolerance": self.tolerance_spin.value(),
            "transform": PeriodicTransform(self.dx_spin.value(), self.dy_spin.value()),
        }


class BoundariesPanel(QDockWidget):
    """Manage boundary patches using the current selection in EdgesPanel."""

    def __init__(self, document: Document, edges_panel, parent=None) -> None:
        super().__init__("Boundary Conditions", parent)
        self.document = document
        self.edges_panel = edges_panel

        container = QWidget()
        layout = QVBoxLayout(container)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.currentItemChanged.connect(self._update_buttons)
        layout.addWidget(self.list_widget)

        row = QHBoxLayout()
        self.new_button = QPushButton("New")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        row.addWidget(self.new_button)
        row.addWidget(self.edit_button)
        row.addWidget(self.delete_button)
        layout.addLayout(row)

        self.assign_button = QPushButton("Assign Selected Edges")
        self.remove_button = QPushButton("Remove Selected Edges")
        layout.addWidget(self.assign_button)
        layout.addWidget(self.remove_button)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        layout.addWidget(QLabel("Periodic pairs"))
        self.pairs_list = QListWidget()
        self.pairs_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.pairs_list)
        pair_buttons = QHBoxLayout()
        self.new_pair_button = QPushButton("New pair")
        self.delete_pair_button = QPushButton("Delete pair")
        pair_buttons.addWidget(self.new_pair_button)
        pair_buttons.addWidget(self.delete_pair_button)
        layout.addLayout(pair_buttons)
        self.setWidget(container)

        self.new_button.clicked.connect(self._on_new)
        self.edit_button.clicked.connect(self._on_edit)
        self.delete_button.clicked.connect(self._on_delete)
        self.assign_button.clicked.connect(self._on_assign)
        self.remove_button.clicked.connect(self._on_remove)
        self.new_pair_button.clicked.connect(self._on_new_pair)
        self.delete_pair_button.clicked.connect(self._on_delete_pair)
        self.pairs_list.itemSelectionChanged.connect(self._update_buttons)
        self.document.boundaries_changed.connect(self.refresh)
        self.document.blocks_changed.connect(self.refresh_status)
        self.refresh()

    def selected_patch_id(self):
        item = self.list_widget.currentItem()
        return None if item is None else int(item.data(PATCH_ID_ROLE))

    def refresh(self) -> None:
        selected = self.selected_patch_id()
        self.list_widget.clear()
        for patch in self.document.boundaries.patches():
            item = QListWidgetItem(
                "{} [{}] - {} edge{}".format(
                    patch.name,
                    patch.boundary_type.value,
                    len(patch.edge_ids),
                    "" if len(patch.edge_ids) == 1 else "s",
                )
            )
            item.setData(PATCH_ID_ROLE, patch.id)
            self.list_widget.addItem(item)
            if patch.id == selected:
                self.list_widget.setCurrentItem(item)
        self._refresh_periodic_pairs()
        self._update_buttons()
        self.refresh_status()

    def _refresh_periodic_pairs(self) -> None:
        selected_pair_id = None
        current_item = self.pairs_list.currentItem()
        if current_item is not None:
            selected_pair_id = current_item.data(PAIR_ID_ROLE)

        self.pairs_list.clear()
        for pair in self.document.boundaries.periodic_pairs():
            source = self.document.boundaries.get_patch(pair.source_patch_id)
            target = self.document.boundaries.get_patch(pair.target_patch_id)
            orientation = "reversed" if pair.reversed else "direct"
            item = QListWidgetItem(
                "{}: {} -> {} [{}], d=({:.6g}, {:.6g})".format(
                    pair.name,
                    source.name,
                    target.name,
                    orientation,
                    pair.transform.translation_x,
                    pair.transform.translation_y,
                )
            )
            item.setData(PAIR_ID_ROLE, pair.id)
            self.pairs_list.addItem(item)
            if pair.id == selected_pair_id:
                self.pairs_list.setCurrentItem(item)

    def refresh_status(self) -> None:
        usage = find_edge_uses(self.document.blocks)
        if not usage:
            self.status.setText("Create blocks before assigning boundary edges.")
            return
        result = self.document.boundaries.validate(self.document.blocks)
        unassigned = sum(
            issue.code.value == "unassigned_external_edge" for issue in result.issues
        )
        invalid = len(result.issues) - unassigned
        if result.is_valid:
            self.status.setText("Boundary definition is valid.")
        else:
            self.status.setText(
                "{} unassigned exterior edge(s); {} other issue(s).".format(
                    unassigned, invalid
                )
            )

    def _selected_edge_ids(self):
        if hasattr(self.edges_panel, "selected_edge_ids"):
            return list(self.edges_panel.selected_edge_ids())
        edges = self.document.topology.edges()
        return [
            edges[self.edges_panel.list_widget.row(item)].id
            for item in self.edges_panel.list_widget.selectedItems()
            if 0 <= self.edges_panel.list_widget.row(item) < len(edges)
        ]

    def _update_buttons(self, *args) -> None:
        enabled = self.selected_patch_id() is not None
        self.edit_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)
        self.assign_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)
        available_periodic_patches = sum(
            patch.boundary_type is BoundaryType.PERIODIC
            and self.document.boundaries.periodic_pair_for_patch(patch.id) is None
            for patch in self.document.boundaries.patches()
        )
        self.new_pair_button.setEnabled(available_periodic_patches >= 2)
        self.delete_pair_button.setEnabled(
            self.pairs_list.currentItem() is not None
        )

    def _on_new(self) -> None:
        dialog = BoundaryPatchDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            patch = self.document.add_boundary_patch(*dialog.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Boundary patch", str(exc))
            return
        self._select_patch(patch.id)

    def _on_edit(self) -> None:
        patch_id = self.selected_patch_id()
        if patch_id is None:
            return
        patch = self.document.boundaries.get_patch(patch_id)
        dialog = BoundaryPatchDialog(self, patch.name, patch.boundary_type)
        if dialog.exec_() != QDialog.Accepted:
            return
        name, boundary_type = dialog.values()
        try:
            self.document.rename_boundary_patch(patch_id, name)
            self.document.set_boundary_patch_type(patch_id, boundary_type)
        except ValueError as exc:
            QMessageBox.warning(self, "Boundary patch", str(exc))
            return
        self._select_patch(patch_id)

    def _on_delete(self) -> None:
        patch_id = self.selected_patch_id()
        if patch_id is not None:
            self.document.remove_boundary_patch(patch_id)

    def _on_assign(self) -> None:
        patch_id = self.selected_patch_id()
        edge_ids = self._selected_edge_ids()
        if patch_id is None or not edge_ids:
            self.status.setText("Select a patch and at least one edge.")
            return
        usage = find_edge_uses(self.document.blocks)
        exterior = {edge_id for edge_id, uses in usage.items() if len(uses) == 1}
        accepted = [edge_id for edge_id in edge_ids if edge_id in exterior]
        rejected = len(edge_ids) - len(accepted)
        if accepted:
            self.document.assign_boundary_edges(patch_id, accepted)
        self.status.setText(
            "{} edge(s) assigned; {} non-exterior edge(s) ignored.".format(
                len(accepted), rejected
            )
        )

    def _on_remove(self) -> None:
        patch_id = self.selected_patch_id()
        edge_ids = self._selected_edge_ids()
        if patch_id is None or not edge_ids:
            self.status.setText("Select a patch and at least one edge.")
            return
        self.document.unassign_boundary_edges(patch_id, edge_ids)
        self.status.setText("{} edge(s) removed from the patch.".format(len(edge_ids)))

    def _on_new_pair(self) -> None:
        available = [
            patch for patch in self.document.boundaries.patches()
            if patch.boundary_type is BoundaryType.PERIODIC
            and self.document.boundaries.periodic_pair_for_patch(patch.id) is None
        ]
        if len(available) < 2:
            self.status.setText("At least two unpaired periodic patches are required.")
            return
        dialog = PeriodicPairDialog(available, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            self.document.add_periodic_pair(**dialog.values())
        except (KeyError, ValueError) as exc:
            QMessageBox.warning(self, "Periodic pair", str(exc))

    def _on_delete_pair(self) -> None:
        item = self.pairs_list.currentItem()
        if item is not None:
            self.document.remove_periodic_pair(int(item.data(PAIR_ID_ROLE)))

    def _select_patch(self, patch_id: int) -> None:
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item.data(PATCH_ID_ROLE) == patch_id:
                self.list_widget.setCurrentItem(item)
                return
