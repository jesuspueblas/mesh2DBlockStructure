import math

import pytest

from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.distribution import BiasedDistribution


def test_rejects_nonpositive_bias():
    with pytest.raises(ValueError):
        BiasedDistribution(bias=0.0)
    with pytest.raises(ValueError):
        BiasedDistribution(bias=-1.0)


def test_bias_one_equals_uniform():
    d = BiasedDistribution(bias=1.0)
    ts = d.positions(5)
    expected = [i / 4 for i in range(5)]
    for a, b in zip(ts, expected):
        assert math.isclose(a, b)


def test_endpoints_fixed():
    d = BiasedDistribution(bias=2.0)
    ts = d.positions(6)
    assert math.isclose(ts[0], 0.0)
    assert math.isclose(ts[-1], 1.0)


def test_strictly_increasing():
    d = BiasedDistribution(bias=1.5)
    ts = d.positions(8)
    for i in range(len(ts) - 1):
        assert ts[i] < ts[i + 1]


def test_bias_gt_one_clusters_at_start():
    # With bias > 1, the first intervals are smaller.
    d = BiasedDistribution(bias=2.0, from_start=True)
    ts = d.positions(6)
    first_interval = ts[1] - ts[0]
    last_interval = ts[-1] - ts[-2]
    assert first_interval < last_interval


def test_bias_gt_one_from_end_clusters_at_end():
    d = BiasedDistribution(bias=2.0, from_start=False)
    ts = d.positions(6)
    first_interval = ts[1] - ts[0]
    last_interval = ts[-1] - ts[-2]
    assert first_interval > last_interval


def test_sample_on_line():
    d = BiasedDistribution(bias=2.0)
    line = Line(Point2D(0, 0), Point2D(1, 0))
    pts = d.sample(line, 5)
    assert len(pts) == 5
    assert math.isclose(pts[0].x, 0.0)
    assert math.isclose(pts[-1].x, 1.0)
