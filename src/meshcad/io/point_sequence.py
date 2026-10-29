"""Import ordered 2D point sequences from CSV files."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from meshcad.core.geometry.point import Point2D


def load_point_sequence(path: Path) -> list[Point2D]:
    """Read an ordered X,Y sequence, optionally preceded by an X,Y header."""
    points: list[Point2D] = []
    first_row = True
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        for row_number, row in enumerate(csv.reader(source), start=1):
            if not row or all(not value.strip() for value in row):
                continue
            if first_row:
                first_row = False
                if len(row) == 2 and tuple(value.strip().lower() for value in row) == ("x", "y"):
                    continue
            if len(row) != 2:
                raise ValueError(
                    f"Row {row_number} must contain exactly two comma-separated coordinates."
                )
            try:
                x, y = (float(value.strip()) for value in row)
            except ValueError as error:
                raise ValueError(
                    f"Row {row_number} contains a non-numeric coordinate."
                ) from error
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError(
                    f"Row {row_number} contains a non-finite coordinate."
                )
            point = Point2D(x, y)
            if points and point == points[-1]:
                raise ValueError(
                    f"Row {row_number} repeats the previous point, creating a zero-length segment."
                )
            points.append(point)

    if len(points) < 2:
        raise ValueError("The point sequence must contain at least two points.")
    return points
