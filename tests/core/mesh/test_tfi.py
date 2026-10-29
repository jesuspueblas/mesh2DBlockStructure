import math

import pytest

from meshcad.core.geometry.point import Point2D
from meshcad.core.mesh.tfi import tfi_grid


def make_rect_sides(n_u=3, n_v=4):
    # Rectangle [0, 1] x [0, 2].
    c0 = Point2D(0, 0)
    c1 = Point2D(1, 0)
    c2 = Point2D(1, 2)
    c3 = Point2D(0, 2)

    south = [Point2D(i / (n_u - 1), 0.0) for i in range(n_u)]
    east = [Point2D(1.0, 2.0 * j / (n_v - 1)) for j in range(n_v)]
    north = [Point2D(1.0 - i / (n_u - 1), 2.0) for i in range(n_u)]  # c2 -> c3
    west = [Point2D(0.0, 2.0 - 2.0 * j / (n_v - 1)) for j in range(n_v)]  # c3 -> c0
    return south, east, north, west


def test_grid_dimensions():
    s, e, n, w = make_rect_sides(3, 4)
    grid = tfi_grid(s, e, n, w)
    assert len(grid) == 4       # n_v rows
    assert len(grid[0]) == 3    # n_u columns


def test_grid_corners():
    s, e, n, w = make_rect_sides(3, 4)
    grid = tfi_grid(s, e, n, w)
    assert grid[0][0] == Point2D(0, 0)      # c0
    assert grid[0][-1] == Point2D(1, 0)     # c1
    assert grid[-1][-1] == Point2D(1, 2)    # c2
    assert grid[-1][0] == Point2D(0, 2)     # c3


def test_grid_boundaries_match_sides():
    s, e, n, w = make_rect_sides(5, 6)
    grid = tfi_grid(s, e, n, w)
    n_u = len(s)
    n_v = len(e)

    # South: row 0 == south.
    for i in range(n_u):
        assert math.isclose(grid[0][i].x, s[i].x)
        assert math.isclose(grid[0][i].y, s[i].y)

    # East: column n_u-1 == east.
    for j in range(n_v):
        assert math.isclose(grid[j][n_u - 1].x, e[j].x)
        assert math.isclose(grid[j][n_u - 1].y, e[j].y)

    # North: row n_v-1 == reversed north.
    for i in range(n_u):
        assert math.isclose(grid[n_v - 1][i].x, n[n_u - 1 - i].x)
        assert math.isclose(grid[n_v - 1][i].y, n[n_u - 1 - i].y)

    # West: column 0 == reversed west.
    for j in range(n_v):
        assert math.isclose(grid[j][0].x, w[n_v - 1 - j].x)
        assert math.isclose(grid[j][0].y, w[n_v - 1 - j].y)


def test_rectangle_interior_is_cartesian():
    # With uniform distribution, a rectangular mesh must be Cartesian.
    s, e, n, w = make_rect_sides(4, 5)
    grid = tfi_grid(s, e, n, w)
    for j in range(len(grid)):
        for i in range(len(grid[0])):
            expected_x = i / (len(grid[0]) - 1)
            expected_y = 2.0 * j / (len(grid) - 1)
            assert math.isclose(grid[j][i].x, expected_x)
            assert math.isclose(grid[j][i].y, expected_y)


def test_requires_matching_counts():
    s = [Point2D(0, 0), Point2D(1, 0), Point2D(2, 0)]
    e = [Point2D(2, 0), Point2D(2, 1)]
    n_wrong = [Point2D(2, 1), Point2D(0, 1)]  # Only 2 points instead of 3.
    w = [Point2D(0, 1), Point2D(0, 0)]
    with pytest.raises(ValueError):
        tfi_grid(s, e, n_wrong, w)


def test_requires_min_two_points():
    with pytest.raises(ValueError):
        tfi_grid([Point2D(0, 0)], [], [], [])
