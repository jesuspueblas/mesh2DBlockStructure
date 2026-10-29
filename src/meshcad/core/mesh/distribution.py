"""Node distributions along a geometric entity."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from meshcad.core.geometry.entity import GeometryEntity
from meshcad.core.geometry.point import Point2D


class NodeDistribution(ABC):
    """Interface for node distributions.

    A distribution produces a strictly increasing list of parameters t in
    [0, 1], with the first value equal to 0 and the last equal to 1.
    """

    @abstractmethod
    def positions(self, n: int) -> List[float]:
        """Return n parameters in [0, 1] with fixed endpoints."""

    def sample(self, geometry: GeometryEntity, n: int) -> List[Point2D]:
        return [geometry.evaluate(t) for t in self.positions(n)]

    def __repr__(self) -> str:  # pragma: no cover
        return self.__class__.__name__ + "()"


class UniformDistribution(NodeDistribution):
    """Uniform distribution in parameter t."""

    def positions(self, n: int) -> List[float]:
        if n < 2:
            raise ValueError("n must be >= 2")
        return [i / (n - 1) for i in range(n)]


@dataclass(frozen=True)
class BiasedDistribution(NodeDistribution):
    """Geometric progression distribution.

    The intervals between nodes grow geometrically by the 'bias' ratio.
    A bias of 1.0 is equivalent to uniform spacing. A bias greater than 1
    concentrates nodes at the start (from_start=True) or end
    (from_start=False).
    """

    bias: float = 2.0
    from_start: bool = True

    def __post_init__(self):
        if self.bias <= 0:
            raise ValueError("bias must be > 0")

    def positions(self, n: int) -> List[float]:
        if n < 2:
            raise ValueError("n must be >= 2")

        if abs(self.bias - 1.0) < 1e-12:
            return [i / (n - 1) for i in range(n)]

        r = self.bias
        denom = r ** (n - 1) - 1.0
        ts = [(r ** i - 1.0) / denom for i in range(n)]

        if self.from_start:
            return ts
        return [1.0 - t for t in reversed(ts)]

    def __repr__(self) -> str:
        return "BiasedDistribution(bias={:g}, from_start={})".format(
            self.bias, self.from_start
        )
