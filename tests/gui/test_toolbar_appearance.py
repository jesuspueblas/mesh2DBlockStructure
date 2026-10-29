from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QToolBar

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
               w.action_split_edge, w.action_insert_point, w.action_mesh, w.action_clear_mesh,
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
    assert not w.orthogonal_check.icon().isNull()


def test_orthogonal_parameters_are_hidden_until_enabled(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1800, 800)
    window.show()
    qtbot.wait(20)

    assert not window.orthogonal_controls_action.isVisible()
    assert not window.smoothing_iterations_spin.isHidden()
    assert not window.smoothing_relaxation_spin.isHidden()

    window.orthogonal_check.setChecked(True)
    assert window.orthogonal_controls_action.isVisible()
    actions = window.mesh_options_toolbar.actions()
    smoothing_action = next(
        action
        for action in actions
        if window.mesh_options_toolbar.widgetForAction(action)
        is window.smoothing_relaxation_spin
    )
    orthogonal_action = next(
        action
        for action in actions
        if window.mesh_options_toolbar.widgetForAction(action)
        is window.orthogonal_check
    )
    assert actions.index(orthogonal_action) > actions.index(smoothing_action)
    assert actions.index(window.orthogonal_controls_action) > actions.index(
        orthogonal_action
    )

    window.orthogonal_check.setChecked(False)
    assert not window.orthogonal_controls_action.isVisible()


def test_toolbars_are_split_into_movable_groups(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1290, 800)
    window.show()
    qtbot.wait(20)

    toolbars = window.findChildren(QToolBar)
    assert len(toolbars) == 3
    assert {toolbar.objectName() for toolbar in toolbars} == {
        "main_toolbar",
        "mesh_view_toolbar",
        "mesh_options_toolbar",
    }
    assert all(toolbar.isMovable() for toolbar in toolbars)
    assert all(
        window.toolBarArea(toolbar) == Qt.TopToolBarArea
        for toolbar in toolbars
    )
    assert window.geometry_toolbar.geometry().top() < window.mesh_view_toolbar.geometry().top()
    assert window.mesh_view_toolbar.geometry().top() == window.mesh_options_toolbar.geometry().top()


def test_right_panel_actions_have_icons_and_tooltips(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    buttons = (
        window.edges_panel.refresh_button,
        window.edges_panel.apply_button,
        window.edges_panel.delete_button,
        window.edges_panel.split_button,
        window.edges_panel.split_coordinates_button,
        window.blocks_panel.delete_button,
        window.patches_panel.new_button,
        window.patches_panel.edit_button,
        window.patches_panel.delete_button,
        window.patches_panel.assign_button,
        window.patches_panel.remove_button,
    )

    assert all(not button.icon().isNull() for button in buttons)
    assert all(button.toolTip().strip() for button in buttons)
