"""Panel listing blocks and the status of their opposite sides."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDockWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meshcad.gui.action_icons import configure_button
from meshcad.gui.document import Document


class BlocksPanel(QDockWidget):
    def __init__(self, document: Document, parent=None) -> None:
        super().__init__("Blocks", parent)
        self.document = document

        container = QWidget()
        layout = QVBoxLayout(container)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.list_widget)

        self.delete_button = QPushButton("Delete Selected Block")
        configure_button(
            self.delete_button, "delete_block", "Delete the selected block."
        )
        self.delete_button.clicked.connect(self._on_delete)
        layout.addWidget(self.delete_button)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.setWidget(container)

        self.document.blocks_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        self.list_widget.clear()
        n_ok, n_bad = 0, 0
        for block in self.document.blocks:
            n0, n1, n2, n3 = [s.node_count for s in block.sides]
            ok_02 = (n0 == n2)
            ok_13 = (n1 == n3)
            if ok_02 and ok_13:
                tag = "OK"
                n_ok += 1
                detail = "(nodes {} x {})".format(n0, n1)
            else:
                tag = "MISMATCH"
                n_bad += 1
                msgs = []
                if not ok_02: msgs.append("sides 0/2: {} vs {}".format(n0, n2))
                if not ok_13: msgs.append("sides 1/3: {} vs {}".format(n1, n3))
                detail = "; ".join(msgs)

            item = QListWidgetItem("Block {}: {} {}".format(block.id, tag, detail))
            self.list_widget.addItem(item)

        if not self.document.blocks:
            self.status.setText("No blocks yet.")
        else:
            self.status.setText("{} blocks: {} OK, {} with mismatches".format(len(self.document.blocks), n_ok, n_bad))

    def _on_delete(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.document.blocks):
            self.status.setText("Select a block to delete.")
            return
        block = self.document.blocks[row]
        self.document.remove_block(block.id)
        self.refresh()
