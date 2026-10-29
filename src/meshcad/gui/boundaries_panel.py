"""Editor for neutral exterior mesh patches."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meshcad.gui.action_icons import configure_button

PATCH_ID_ROLE=Qt.UserRole
class BoundariesPanel(QDockWidget):
    def __init__(self,document,edges_panel=None,parent=None):
        super().__init__("Mesh Patches",parent); self.document=document; self.edges_panel=edges_panel
        root=QWidget(); layout=QVBoxLayout(root); self.list_widget=QListWidget(); layout.addWidget(self.list_widget)
        row=QHBoxLayout(); self.new_button=QPushButton("New"); self.edit_button=QPushButton("Rename"); self.delete_button=QPushButton("Delete")
        configure_button(self.new_button, "new", "Create a mesh patch.")
        configure_button(self.edit_button, "rename", "Rename the selected mesh patch.")
        configure_button(self.delete_button, "delete", "Delete the selected mesh patch.")
        for b in (self.new_button,self.edit_button,self.delete_button): row.addWidget(b)
        layout.addLayout(row); self.assign_button=QPushButton("Assign selected edges"); self.remove_button=QPushButton("Remove selected edges"); layout.addWidget(self.assign_button); layout.addWidget(self.remove_button); self.status=QLabel(); layout.addWidget(self.status); self.setWidget(root)
        configure_button(
            self.assign_button, "assign", "Assign selected edges to this mesh patch."
        )
        configure_button(
            self.remove_button, "remove", "Remove selected edges from this mesh patch."
        )
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        self.new_button.clicked.connect(self._new); self.edit_button.clicked.connect(self._rename); self.delete_button.clicked.connect(self._delete); self.assign_button.clicked.connect(self._assign); self.remove_button.clicked.connect(self._remove)
        document.patches_changed.connect(self.refresh); self.refresh()
    def selected_patch_id(self):
        item=self.list_widget.currentItem(); return None if item is None else int(item.data(PATCH_ID_ROLE))
    def refresh(self):
        selected=self.selected_patch_id(); self.list_widget.blockSignals(True); self.list_widget.clear()
        for patch in self.document.patches.patches():
            item=QListWidgetItem(f"{patch.name} ({len(patch.edge_ids)} edges)"); item.setData(PATCH_ID_ROLE,patch.id); self.list_widget.addItem(item)
            if patch.id==selected:self.list_widget.setCurrentItem(item)
        self.list_widget.blockSignals(False)
        self._on_selection_changed()
    def _on_selection_changed(self, row=None):
        patch_id=self.selected_patch_id()
        edge_ids=[] if patch_id is None else self.document.patches.get_patch(patch_id).edge_ids
        if self.edges_panel is not None:self.edges_panel.select_edges(edge_ids)
    def _new(self):
        name,ok=QInputDialog.getText(self,"New mesh patch","Name:")
        if ok and name.strip():self.document.add_mesh_patch(name)
    def _rename(self):
        pid=self.selected_patch_id()
        if pid is None:return
        name,ok=QInputDialog.getText(self,"Rename mesh patch","Name:",text=self.document.patches.get_patch(pid).name)
        if ok and name.strip():self.document.rename_mesh_patch(pid,name)
    def _delete(self):
        pid=self.selected_patch_id()
        if pid is not None:self.document.remove_mesh_patch(pid)
    def _selected_edges(self):
        return [] if self.edges_panel is None else self.edges_panel.selected_edge_ids()
    def _assign(self):
        pid=self.selected_patch_id(); edges=self._selected_edges()
        if pid is not None and edges:
            try:
                self.document.assign_mesh_patch_edges(pid, edges)
            except ValueError as error:
                self.status.setText(str(error))
                return
            self.status.setText("Assigned {} exterior edges.".format(len(edges)))
    def _remove(self):
        pid=self.selected_patch_id(); edges=self._selected_edges()
        if pid is not None and edges:self.document.unassign_mesh_patch_edges(pid,edges)
