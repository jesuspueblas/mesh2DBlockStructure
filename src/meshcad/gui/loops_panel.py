"""Panel listing detected loops."""

from __future__ import annotations
from PyQt5.QtWidgets import QDockWidget, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget
from meshcad.core.topology.block import Block
from meshcad.core.topology.loop_detector import find_loops
from meshcad.gui.document import Document
from meshcad.gui.tools.corner_picker import CornerPickerTool


class LoopsPanel(QDockWidget):
    def __init__(self, document: Document, canvas, parent=None) -> None:
        super().__init__("Loops", parent)
        self.document = document
        self.canvas = canvas
        self.loops = []

        container = QWidget()
        layout = QVBoxLayout(container)

        self.find_button = QPushButton("Detect Loops")
        self.find_button.clicked.connect(self._on_find)
        layout.addWidget(self.find_button)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

        self.create_button = QPushButton("Create Block from Loop")
        self.create_button.clicked.connect(self._on_create_block)
        layout.addWidget(self.create_button)

        self.status = QLabel("Click 'Detect Loops'.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.setWidget(container)

    def _on_find(self) -> None:
        self.loops = find_loops(self.document.topology)
        self.list_widget.clear()
        if not self.loops:
            self.status.setText("No closed loops were detected.")
            return
        for i, loop in enumerate(self.loops):
            item = QListWidgetItem("Loop {}: {} edges".format(i, len(loop)))
            self.list_widget.addItem(item)
        self.status.setText("Detected {} loops. Select one and create the block.".format(len(self.loops)))

    def _on_selection_changed(self, row: int) -> None:
        if row < 0 or row >= len(self.loops):
            self.canvas.clear_highlight()
            return
        self.canvas.highlight_loop(self.loops[row])

    def _on_create_block(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.loops):
            self.status.setText("Select a loop first.")
            return
        loop = self.loops[row]
        tool = CornerPickerTool(self.canvas, loop, self._on_corners_picked)
        self.canvas.set_tool(tool)
        self._active_loop = loop
        self.status.setText(
            "Click four loop vertices for the block corners. Any additional "
            "loop edges between corners will form part of that block side."
        )

    def _on_corners_picked(self, corner_ids) -> None:
        loop = self._active_loop
        try:
            sides = loop.split_at_corners(self.document.topology, corner_ids)
            block = Block(self.document.next_block_id(), sides)
            block.validate_opposite_sides()
        except ValueError as e:
            self.status.setText("Error: {}".format(e))
            return
        self.document.add_block(block)
        self.status.setText("Block {} created.".format(block.id))
