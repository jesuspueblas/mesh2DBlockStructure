"""The IO layer only handles dictionaries; it does not import Qt."""

import sys


def test_io_package_does_not_import_qt():
    """Importar meshcad.io no must arrastrar PyQt5."""
    for name in list(sys.modules):
        if name.startswith("PyQt5") or name.startswith("meshcad.gui"):
            del sys.modules[name]

    import meshcad.io  # noqa: F401

    assert "meshcad.gui" not in sys.modules
    assert "meshcad.gui.document" not in sys.modules


def test_save_and_load_round_trip(tmp_path):
    from meshcad.io.project_io import load_project, save_project

    data = {
        "format": "meshcad-project",
        "version": 1,
        "payload": {"a": 1, "b": [2, 3]},
    }
    path = tmp_path / "p.json"
    save_project(data, path)
    assert path.exists()
    back = load_project(path)
    assert back == data


def test_save_creates_parent_dirs(tmp_path):
    from meshcad.io.project_io import save_project

    path = tmp_path / "a" / "b" / "p.json"
    save_project({"k": "v"}, path)
    assert path.exists()
