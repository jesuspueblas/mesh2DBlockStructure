import math

import pytest

from meshcad.core.geometry.point import Point2D
from meshcad.io.point_sequence import load_point_sequence


def test_load_point_sequence_with_optional_header_and_blank_lines(tmp_path):
    path = tmp_path / "points.csv"
    path.write_text("\ufeffX,Y\n0,0\n\n1.5,2\n3,0\n", encoding="utf-8")

    assert load_point_sequence(path) == [
        Point2D(0, 0),
        Point2D(1.5, 2),
        Point2D(3, 0),
    ]


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("0,0\n1\n", "Row 2 must contain exactly two"),
        ("0,0\nx,1\n", "Row 2 contains a non-numeric"),
        ("0,0\ninf,1\n", "Row 2 contains a non-finite"),
        ("0,0\n0,0\n", "Row 2 repeats the previous point"),
        ("X,Y\n0,0\n", "at least two points"),
    ],
)
def test_load_point_sequence_rejects_invalid_input(tmp_path, contents, message):
    path = tmp_path / "invalid.csv"
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_point_sequence(path)


def test_load_point_sequence_preserves_point_order(tmp_path):
    path = tmp_path / "ordered.csv"
    path.write_text("0,0\n2,1\n1,3\n4,2\n", encoding="utf-8")

    points = load_point_sequence(path)

    assert [point.x for point in points] == [0, 2, 1, 4]
    assert all(math.isfinite(point.y) for point in points)
