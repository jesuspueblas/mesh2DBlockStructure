"""Periodic boundary pairing for two-dimensional structured meshes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple
import math


@dataclass(frozen=True)
class PeriodicTransform:
    """A translational transform from the source patch to the target patch."""

    translation_x: float = 0.0
    translation_y: float = 0.0

    def apply(self, point: Sequence[float]) -> Tuple[float, float]:
        return (float(point[0]) + self.translation_x,
                float(point[1]) + self.translation_y)


@dataclass(frozen=True)
class PeriodicPair:
    """A one-to-one relation between two periodic boundary patches."""

    id: int
    name: str
    source_patch_id: int
    target_patch_id: int
    reversed: bool = False
    tolerance: float = 1.0e-8
    transform: PeriodicTransform = PeriodicTransform()

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("Periodic pair name must not be empty")
        if self.source_patch_id == self.target_patch_id:
            raise ValueError("A periodic patch cannot be paired with itself")
        if not math.isfinite(self.tolerance) or self.tolerance <= 0.0:
            raise ValueError("Periodic tolerance must be a positive finite number")
        if not math.isfinite(self.transform.translation_x) or not math.isfinite(
            self.transform.translation_y
        ):
            raise ValueError("Periodic translation must be finite")
        if name != self.name:
            object.__setattr__(self, "name", name)


@dataclass(frozen=True)
class PeriodicMatchResult:
    """Result of comparing two ordered point sequences."""

    is_compatible: bool
    reversed: bool
    max_error: float
    transform: PeriodicTransform
    message: str = ""


def match_periodic_points(
    source_points: Sequence[Sequence[float]],
    target_points: Sequence[Sequence[float]],
    tolerance: float = 1.0e-8,
) -> PeriodicMatchResult:
    """Find the best translational direct/reversed point correspondence.

    Translation is inferred from the first matched point. Both orientations
    are tested and the one with the smallest maximum Euclidean error wins.
    """
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("Periodic tolerance must be a positive finite number")
    if len(source_points) != len(target_points):
        return PeriodicMatchResult(
            False, False, math.inf, PeriodicTransform(),
            "Periodic patches have different node counts",
        )
    if not source_points:
        return PeriodicMatchResult(
            False, False, math.inf, PeriodicTransform(),
            "Periodic patches contain no nodes",
        )

    def candidate(reverse: bool):
        target = list(reversed(target_points)) if reverse else list(target_points)
        dx = float(target[0][0]) - float(source_points[0][0])
        dy = float(target[0][1]) - float(source_points[0][1])
        errors = [
            math.hypot(
                float(t[0]) - (float(s[0]) + dx),
                float(t[1]) - (float(s[1]) + dy),
            )
            for s, t in zip(source_points, target)
        ]
        return max(errors), PeriodicTransform(dx, dy)

    direct_error, direct_transform = candidate(False)
    reverse_error, reverse_transform = candidate(True)
    if reverse_error < direct_error:
        reverse, error, transform = True, reverse_error, reverse_transform
    else:
        reverse, error, transform = False, direct_error, direct_transform
    return PeriodicMatchResult(
        error <= tolerance,
        reverse,
        error,
        transform,
        "" if error <= tolerance else "Periodic points do not match within tolerance",
    )
