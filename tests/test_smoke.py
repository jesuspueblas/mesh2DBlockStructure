"""Smoke test: the package imports and exposes a version."""


def test_version():
    import meshcad

    assert isinstance(meshcad.__version__, str)
    assert meshcad.__version__
