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


def test_periodic_pair_list_and_buttons(qtbot):
    doc = Document()
    a = doc.add_boundary_patch("bottom", BoundaryType.PERIODIC)
    b = doc.add_boundary_patch("top", BoundaryType.PERIODIC)
    panel = BoundariesPanel(doc, FakeEdgesPanel())
    qtbot.addWidget(panel)
    assert panel.new_pair_button.isEnabled()
    pair = doc.add_periodic_pair("vertical", a.id, b.id)
    assert panel.pairs_list.count() == 1
    assert "vertical: bottom -> top [direct]" in panel.pairs_list.item(0).text()
    assert panel.new_pair_button.isEnabled() is False
    panel.pairs_list.setCurrentRow(0)
    assert panel.delete_pair_button.isEnabled()
    panel._on_delete_pair()
    assert doc.boundaries.periodic_pairs() == ()


def test_periodic_pair_dialog_values(qtbot):
    from meshcad.core.boundary import BoundaryModel, PeriodicTransform
    from meshcad.gui.boundaries_panel import PeriodicPairDialog
    model = BoundaryModel()
    a = model.add_patch("a", BoundaryType.PERIODIC)
    b = model.add_patch("b", BoundaryType.PERIODIC)
    dialog = PeriodicPairDialog([a, b])
    qtbot.addWidget(dialog)
    dialog.name_edit.setText("pair")
    dialog.reversed_check.setChecked(True)
    dialog.dx_spin.setValue(2.5)
    dialog.dy_spin.setValue(-1.25)
    values = dialog.values()
    assert values["source_patch_id"] == a.id
    assert values["target_patch_id"] == b.id
    assert values["reversed"] is True
    assert values["transform"] == PeriodicTransform(2.5, -1.25)
