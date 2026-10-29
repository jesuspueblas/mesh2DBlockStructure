from PyQt5.QtCore import Qt
from meshcad.gui.main_window import MainWindow


def test_drawing_toolbar_checks_active_tool(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)

    assert w.action_select.isChecked()
    assert not any(
        action.isChecked()
        for action in (w.action_line, w.action_arc, w.action_spline)
    )

    for selected, others in (
        (w.action_line, (w.action_select, w.action_arc, w.action_spline)),
        (w.action_arc, (w.action_select, w.action_line, w.action_spline)),
        (w.action_spline, (w.action_select, w.action_line, w.action_arc)),
    ):
        selected.trigger()
        assert selected.isChecked()
        assert all(not action.isChecked() for action in others)

    qtbot.keyClick(w.canvas, Qt.Key_Escape)
    assert w.action_select.isChecked()
    assert not any(
        action.isChecked()
        for action in (w.action_line, w.action_arc, w.action_spline)
    )


def test_toolbar_actions_have_icons_and_tooltips(qtbot):
    w = MainWindow(); qtbot.addWidget(w)
    actions = (w.action_select, w.action_line, w.action_arc, w.action_spline,
               w.action_insert_point, w.action_mesh, w.action_clear_mesh,
               w.action_grid, w.action_reset_zoom)
    assert all(not action.icon().isNull() for action in actions)
    assert all(action.toolTip().strip() for action in actions)
    assert all(action.statusTip().strip() for action in actions)


def test_toolbar_visual_configuration(qtbot):
    w = MainWindow(); qtbot.addWidget(w)
    toolbar = w.findChild(type(w.findChild(__import__('PyQt5.QtWidgets', fromlist=['QToolBar']).QToolBar)), 'main_toolbar')
    assert toolbar is not None
    assert toolbar.iconSize().width() == 24
    assert toolbar.toolButtonStyle() == Qt.ToolButtonTextBesideIcon


def test_mesh_controls_have_tooltips(qtbot):
    w = MainWindow(); qtbot.addWidget(w)
    controls = (w.grid_spin, w.orthogonal_check, w.orthogonal_layers_spin,
                w.orthogonal_strength_spin, w.smoothing_iterations_spin,
                w.smoothing_relaxation_spin)
    assert all(control.toolTip().strip() for control in controls)
