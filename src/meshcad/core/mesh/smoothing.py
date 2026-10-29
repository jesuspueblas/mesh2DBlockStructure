"""Boundary orthogonalization and elliptic smoothing for 2D meshes."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple
from meshcad.core.geometry.point import Point2D
Grid = List[List[Point2D]]
EPS = 1.0e-14

@dataclass(frozen=True)
class SmoothingOptions:
    orthogonal: bool = False
    orthogonal_layers: int = 2
    smoothing_iterations: int = 0
    relaxation: float = 0.45
    orthogonal_strength: float = 0.85
    def __post_init__(self):
        if self.orthogonal_layers < 1: raise ValueError("orthogonal_layers must be >= 1")
        if self.smoothing_iterations < 0: raise ValueError("smoothing_iterations must be >= 0")
        if not 0.0 < self.relaxation <= 1.0: raise ValueError("relaxation must be in (0, 1]")
        if not 0.0 <= self.orthogonal_strength <= 1.0: raise ValueError("orthogonal_strength must be in [0, 1]")

def _copy(g): return [[Point2D(p.x, p.y) for p in row] for row in g]

def _normal(a, b, toward):
    tx, ty = b.x-a.x, b.y-a.y
    n = math.hypot(tx, ty)
    if n <= EPS: return 0.0, 0.0
    nx, ny = -ty/n, tx/n
    mx, my = (a.x+b.x)/2, (a.y+b.y)/2
    if nx*(toward.x-mx)+ny*(toward.y-my) < 0: nx, ny = -nx, -ny
    return nx, ny

def _project(boundary, current, nx, ny, strength):
    if nx == 0.0 and ny == 0.0: return current
    d = (current.x-boundary.x)*nx + (current.y-boundary.y)*ny
    tx, ty = boundary.x+d*nx, boundary.y+d*ny
    return Point2D(current.x+strength*(tx-current.x), current.y+strength*(ty-current.y))

def enforce_boundary_orthogonality(grid: Sequence[Sequence[Point2D]], layers=2, strength=0.85) -> Grid:
    out, source = _copy(grid), _copy(grid)
    nv, nu = len(out), len(out[0]) if out else 0
    if nv < 3 or nu < 3: return out
    layers = min(layers, (nu-1)//2, (nv-1)//2)
    for layer in range(1, layers+1):
        w = strength*(layers-layer+1)/layers
        proposals = {}
        def add(i,j,p): proposals.setdefault((i,j), []).append(p)
        for i in range(1,nu-1):
            nx,ny=_normal(source[0][i-1],source[0][i+1],source[layer][i])
            add(i,layer,_project(source[0][i],source[layer][i],nx,ny,w))
            nx,ny=_normal(source[-1][i-1],source[-1][i+1],source[-1-layer][i])
            add(i,nv-1-layer,_project(source[-1][i],source[-1-layer][i],nx,ny,w))
        for j in range(1,nv-1):
            nx,ny=_normal(source[j-1][0],source[j+1][0],source[j][layer])
            add(layer,j,_project(source[j][0],source[j][layer],nx,ny,w))
            nx,ny=_normal(source[j-1][-1],source[j+1][-1],source[j][nu-1-layer])
            add(nu-1-layer,j,_project(source[j][-1],source[j][nu-1-layer],nx,ny,w))
        for (i,j),pts in proposals.items():
            out[j][i]=Point2D(sum(p.x for p in pts)/len(pts),sum(p.y for p in pts)/len(pts))
        source=_copy(out)
    return out

def _area(a,b,c,d):
    return .5*((a.x*b.y-b.x*a.y)+(b.x*c.y-c.x*b.y)+(c.x*d.y-d.x*c.y)+(d.x*a.y-a.x*d.y))

def _valid(p,g,i,j,sign):
    for cj in (j-1,j):
        for ci in (i-1,i):
            if 0 <= ci < len(g[0])-1 and 0 <= cj < len(g)-1:
                q=[g[cj][ci],g[cj][ci+1],g[cj+1][ci+1],g[cj+1][ci]]
                idx={(ci,cj):0,(ci+1,cj):1,(ci+1,cj+1):2,(ci,cj+1):3}.get((i,j))
                if idx is not None: q[idx]=p
                if _area(*q)*sign <= EPS: return False
    return True

def elliptic_smooth(grid: Sequence[Sequence[Point2D]], iterations=30, relaxation=0.45) -> Grid:
    out=_copy(grid); nv=len(out); nu=len(out[0]) if out else 0
    if iterations == 0 or nv < 3 or nu < 3: return out
    sign=1.0 if _area(out[0][0],out[0][1],out[1][1],out[1][0]) >= 0 else -1.0
    for _ in range(iterations):
        old=_copy(out)
        for j in range(1,nv-1):
            for i in range(1,nu-1):
                p=old[j][i]; ns=(old[j][i-1],old[j][i+1],old[j-1][i],old[j+1][i])
                ax,ay=sum(q.x for q in ns)/4,sum(q.y for q in ns)/4
                c=Point2D(p.x+relaxation*(ax-p.x),p.y+relaxation*(ay-p.y))
                if _valid(c,out,i,j,sign): out[j][i]=c
    return out

def improve_grid(grid, options):
    out=_copy(grid)
    if options.orthogonal:
        out=enforce_boundary_orthogonality(out,options.orthogonal_layers,options.orthogonal_strength)
    if options.smoothing_iterations:
        out=elliptic_smooth(out,options.smoothing_iterations,options.relaxation)
    return out
