"""Neutral geometric patch model, independent of CFD conditions."""
from dataclasses import replace
from typing import Dict, Iterable, Tuple
from meshcad.core.boundary.patch import MeshPatch
from meshcad.core.topology.usage import find_edge_uses

class PatchModel:
    def __init__(self): self._patches: Dict[int,MeshPatch]={}; self._next_patch_id=0
    @property
    def next_patch_id(self): return self._next_patch_id
    def patches(self)->Tuple[MeshPatch,...]: return tuple(self._patches[i] for i in sorted(self._patches))
    def get_patch(self,patch_id):
        try:return self._patches[int(patch_id)]
        except KeyError as e: raise KeyError(f"Unknown mesh patch id: {patch_id}") from e
    def patch_for_edge(self,edge_id): return next((p for p in self.patches() if int(edge_id) in p.edge_ids),None)
    def add_patch(self,name):
        p=MeshPatch(self._next_patch_id,self._unique_name(name)); self._patches[p.id]=p; self._next_patch_id+=1; return p
    def remove_patch(self,patch_id): return self._patches.pop(self.get_patch(patch_id).id)
    def rename_patch(self,patch_id,name):
        p=self.get_patch(patch_id); p=replace(p,name=self._unique_name(name,p.id)); self._patches[p.id]=p; return p
    def assign_edges(self,patch_id,edge_ids:Iterable[int]):
        target=self.get_patch(patch_id); ids=set(map(int,edge_ids))
        for p in self.patches():
            if p.id!=target.id:self._patches[p.id]=replace(p,edge_ids=tuple(e for e in p.edge_ids if e not in ids))
        target=replace(target,edge_ids=tuple(set(target.edge_ids)|ids)); self._patches[target.id]=target; return target
    def unassign_edges(self,patch_id,edge_ids):
        p=self.get_patch(patch_id); ids=set(map(int,edge_ids)); p=replace(p,edge_ids=tuple(e for e in p.edge_ids if e not in ids)); self._patches[p.id]=p; return p
    def discard_edges(self,edge_ids):
        ids=set(map(int,edge_ids))
        for p in self.patches(): self._patches[p.id]=replace(p,edge_ids=tuple(e for e in p.edge_ids if e not in ids))
    def validate(self,blocks):
        usage=find_edge_uses(blocks); external={e for e,u in usage.items() if len(u)==1}; assigned={e for p in self.patches() for e in p.edge_ids}
        issues=[]
        for p in self.patches():
            for e in p.edge_ids:
                if e not in external: issues.append(f"Edge {e} in patch '{p.name}' is not exterior")
        for e in sorted(external-assigned): issues.append(f"External edge {e} has no mesh patch")
        return PatchValidationResult(tuple(issues))
    def _unique_name(self,name,exclude=None):
        name=name.strip()
        if not name: raise ValueError("Mesh patch name must not be empty")
        if any(p.id!=exclude and p.name.casefold()==name.casefold() for p in self.patches()): raise ValueError(f"Mesh patch name already exists: {name}")
        return name
    @classmethod
    def restore(cls,patches,next_patch_id=None,*ignored):
        m=cls()
        for p in patches:
            if p.id in m._patches: raise ValueError(f"Duplicate mesh patch id: {p.id}")
            m._unique_name(p.name); m._patches[p.id]=p
        minimum=max(m._patches,default=-1)+1; m._next_patch_id=minimum if next_patch_id is None else int(next_patch_id)
        return m

class PatchValidationResult:
    def __init__(self,issues=()): self.issues=tuple(issues)
    @property
    def is_valid(self): return not self.issues
