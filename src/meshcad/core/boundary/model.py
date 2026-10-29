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
        target=self.get_patch(patch_id); requested=tuple(map(int,edge_ids)); ids=set(requested)
        if len(ids)!=len(requested):
            raise ValueError("An edge cannot be assigned to a patch more than once")
        existing=set(target.edge_ids)&ids
        if existing:
            raise ValueError(
                "Edge(s) {} are already assigned to patch '{}'".format(
                    ", ".join(map(str, sorted(existing))), target.name
                )
            )
        for patch in self.patches():
            if patch.id == target.id:
                continue
            conflicting = set(patch.edge_ids) & ids
            if conflicting:
                raise ValueError(
                    "Edge(s) {} are already assigned to patch '{}'".format(
                        ", ".join(map(str, sorted(conflicting))), patch.name
                    )
                )
        target=replace(target,edge_ids=target.edge_ids+tuple(sorted(ids))); self._patches[target.id]=target; return target
    def unassign_edges(self,patch_id,edge_ids):
        p=self.get_patch(patch_id); ids=set(map(int,edge_ids)); p=replace(p,edge_ids=tuple(e for e in p.edge_ids if e not in ids)); self._patches[p.id]=p; return p
    def discard_edges(self,edge_ids):
        ids=set(map(int,edge_ids))
        for p in self.patches(): self._patches[p.id]=replace(p,edge_ids=tuple(e for e in p.edge_ids if e not in ids))
    def replace_edge(self,edge_id,new_edge_ids):
        edge_id=int(edge_id); replacements=tuple(map(int,new_edge_ids))
        for patch in self.patches():
            if edge_id in patch.edge_ids:
                edge_ids=tuple(
                    replacement
                    for current in patch.edge_ids
                    for replacement in (replacements if current==edge_id else (current,))
                )
                self._patches[patch.id]=replace(patch,edge_ids=edge_ids)
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
            assigned_edges = {
                edge_id for existing in m.patches() for edge_id in existing.edge_ids
            }
            duplicate_edges = assigned_edges & set(p.edge_ids)
            if duplicate_edges:
                raise ValueError(
                    "Edge(s) {} are assigned to more than one mesh patch".format(
                        ", ".join(map(str, sorted(duplicate_edges)))
                    )
                )
            m._unique_name(p.name); m._patches[p.id]=p
        minimum=max(m._patches,default=-1)+1; m._next_patch_id=minimum if next_patch_id is None else int(next_patch_id)
        return m

class PatchValidationResult:
    def __init__(self,issues=()): self.issues=tuple(issues)
    @property
    def is_valid(self): return not self.issues
