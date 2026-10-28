"""Named geometric patch on the exterior of a mesh."""
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class MeshPatch:
    id: int
    name: str
    edge_ids: Tuple[int, ...] = ()
    def __post_init__(self):
        name=self.name.strip()
        if not name: raise ValueError("Mesh patch name must not be empty")
        object.__setattr__(self,"name",name)
        object.__setattr__(self,"edge_ids",tuple(sorted(set(map(int,self.edge_ids)))))
