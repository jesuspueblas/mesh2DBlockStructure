import math
import pytest
from meshcad.core.boundary import PeriodicPair, PeriodicTransform, match_periodic_points


def test_direct_translational_match():
    result = match_periodic_points([(0, 0), (1, 0), (2, 0)],
                                   [(3, 4), (4, 4), (5, 4)])
    assert result.is_compatible
    assert result.reversed is False
    assert result.transform == PeriodicTransform(3, 4)
    assert result.max_error == pytest.approx(0.0)


def test_reversed_translational_match_is_detected():
    result = match_periodic_points([(0, 0), (1, 0), (2, 0)],
                                   [(5, 4), (4, 4), (3, 4)])
    assert result.is_compatible
    assert result.reversed is True
    assert result.transform == PeriodicTransform(3, 4)


def test_node_count_and_tolerance_failures_are_reported():
    mismatch = match_periodic_points([(0, 0)], [(1, 0), (2, 0)])
    assert not mismatch.is_compatible and math.isinf(mismatch.max_error)
    distorted = match_periodic_points([(0, 0), (1, 0)], [(2, 0), (3, 0.1)], 1e-3)
    assert not distorted.is_compatible


def test_periodic_pair_validates_identity_and_tolerance():
    with pytest.raises(ValueError, match="itself"):
        PeriodicPair(0, "bad", 1, 1)
    with pytest.raises(ValueError, match="positive"):
        PeriodicPair(0, "bad", 1, 2, tolerance=0.0)
