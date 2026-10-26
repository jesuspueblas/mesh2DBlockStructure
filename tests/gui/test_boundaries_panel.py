from meshcad.core.boundary import BoundaryType
from meshcad.gui.boundaries_panel import BoundariesPanel
from meshcad.gui.document import Document


class FakeEdgesPanel:
    def __init__(self, edge_ids=()):
        self.edge_ids = list(edge_ids)

    def selected_edge_ids(self):
        return list(self.edge_ids)


def test_panel_starts_without_patches(qtbot):
    doc = Document()
    panel = BoundariesPanel(doc, FakeEdgesPanel())
    qtbot.addWidget(panel)
    assert panel.list_widget.count() == 0
    assert panel.assign_button.isEnabled() is False


def test_panel_refresh_lists_patch_and_preserves_selection(qtbot):
    doc = Document()
    panel = BoundariesPanel(doc, FakeEdgesPanel())
    qtbot.addWidget(panel)
    patch = doc.add_boundary_patch("inlet", BoundaryType.INLET)
    panel._select_patch(patch.id)
    doc.assign_boundary_edges(patch.id, [7, 8])
    assert panel.list_widget.count() == 1
    assert "inlet [inlet] - 2 edges" in panel.list_widget.currentItem().text()


def test_remove_selected_edges_uses_document_api(qtbot):
    doc = Document()
    patch = doc.add_boundary_patch("wall", BoundaryType.WALL)
    doc.assign_boundary_edges(patch.id, [1, 2])
    panel = BoundariesPanel(doc, FakeEdgesPanel([2]))
    qtbot.addWidget(panel)
    panel._select_patch(patch.id)
    panel._on_remove()
    assert doc.boundaries.get_patch(patch.id).edge_ids == (1,)


def test_delete_patch(qtbot):
    doc = Document()
    patch = doc.add_boundary_patch("wall", BoundaryType.WALL)
    panel = BoundariesPanel(doc, FakeEdgesPanel())
    qtbot.addWidget(panel)
    panel._select_patch(patch.id)
    panel._on_delete()
    assert doc.boundaries.patches() == ()
