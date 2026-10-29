import math

from meshcad.core.geometry.point import Point2D
from meshcad.core.geometry.vector import Vector2D


def test_create():
    p = Point2D(1.0, 2.0)
    assert p.x == 1.0
    assert p.y == 2.0


def test_subtraction_gives_vector():
    v = Point2D(3, 4) - Point2D(1, 1)
    assert isinstance(v, Vector2D)
    assert v.x == 2
    assert v.y == 3


def test_addition_with_vector():
    p = Point2D(1, 1) + Vector2D(2, 3)
    assert p == Point2D(3, 4)


def test_distance():
    d = Point2D(0, 0).distance_to(Point2D(3, 4))
    assert math.isclose(d, 5.0)


def test_as_tuple():
    assert Point2D(1, 2).as_tuple() == (1, 2)


def test_immutable():
    p = Point2D(1, 2)
    try:
        p.x = 10
    except Exception:
        return
    raise AssertionError("Point2D should be immutable")
