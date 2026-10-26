"""JSON serialization of geometry, topology, mesh, and blocks."""

from __future__ import annotations

from typing import Any, Dict, List

from meshcad.core.geometry.arc import Arc
from meshcad.core.geometry.entity import GeometryEntity
from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.geometry.spline import Spline
from meshcad.core.mesh.distribution import (
    BiasedDistribution,
    NodeDistribution,
    UniformDistribution,
)
from meshcad.core.mesh.model import EdgeMeshSpec
from meshcad.core.topology.block import Block
from meshcad.core.topology.block_side import BlockSide
from meshcad.core.topology.edge import Edge, OrientedEdge
from meshcad.core.topology.topology import Topology
from meshcad.core.topology.vertex import Vertex


# ------------------------------- helpers ------------------------------- #


def _point_to_list(p: Point2D) -> List[float]:
    return [p.x, p.y]


def _point_from_list(data) -> Point2D:
    return Point2D(float(data[0]), float(data[1]))


# ------------------------------ geometry ------------------------------ #


def geometry_to_dict(g: GeometryEntity) -> Dict[str, Any]:
    if isinstance(g, Line):
        return {
            "type": "line",
            "start": _point_to_list(g.start),
            "end": _point_to_list(g.end),
        }
    if isinstance(g, Arc):
        return {
            "type": "arc",
            "center": _point_to_list(g.center),
            "radius": g.radius,
            "start_angle": g.start_angle,
            "end_angle": g.end_angle,
        }
    if isinstance(g, Spline):
        return {
            "type": "spline",
            "points": [_point_to_list(p) for p in g.points],
        }
    raise TypeError("Non-serializable geometry type: {}".format(type(g).__name__))


def geometry_from_dict(data: Dict[str, Any]) -> GeometryEntity:
    t = data.get("type")
    if t == "line":
        return Line(_point_from_list(data["start"]), _point_from_list(data["end"]))
    if t == "arc":
        return Arc(
            _point_from_list(data["center"]),
            float(data["radius"]),
            float(data["start_angle"]),
            float(data["end_angle"]),
        )
    if t == "spline":
        pts = tuple(_point_from_list(p) for p in data["points"])
        return Spline(pts)
    raise ValueError("Unknown geometry type: {!r}".format(t))


# --------------------------- distribuciones ---------------------------- #


def distribution_to_dict(d: NodeDistribution) -> Dict[str, Any]:
    if isinstance(d, UniformDistribution):
        return {"type": "uniform"}
    if isinstance(d, BiasedDistribution):
        return {
            "type": "biased",
            "bias": d.bias,
            "from_start": d.from_start,
        }
    raise TypeError("Non-serializable distribution: {}".format(type(d).__name__))


def distribution_from_dict(data: Dict[str, Any]) -> NodeDistribution:
    t = data.get("type")
    if t == "uniform":
        return UniformDistribution()
    if t == "biased":
        return BiasedDistribution(
            bias=float(data["bias"]),
            from_start=bool(data.get("from_start", True)),
        )
    raise ValueError("Unknown distribution: {!r}".format(t))


# ------------------------------ topology ------------------------------ #


def topology_to_dict(t: Topology) -> Dict[str, Any]:
    return {
        "vertices": [
            {"id": v.id, "point": _point_to_list(v.point)} for v in t.vertices()
        ],
        "edges": [
            {
                "id": e.id,
                "start_vertex_id": e.start_vertex_id,
                "end_vertex_id": e.end_vertex_id,
                "geometry": geometry_to_dict(e.geometry),
            }
            for e in t.edges()
        ],
    }


def topology_from_dict(data: Dict[str, Any]) -> Topology:
    t = Topology()
    vertices: Dict[int, Vertex] = {}
    for vd in data.get("vertices", []):
        v = Vertex(int(vd["id"]), _point_from_list(vd["point"]))
        vertices[v.id] = v
    edges: Dict[int, Edge] = {}
    for ed in data.get("edges", []):
        g = geometry_from_dict(ed["geometry"])
        e = Edge(
            int(ed["id"]),
            int(ed["start_vertex_id"]),
            int(ed["end_vertex_id"]),
            g,
        )
        edges[e.id] = e
    t.import_state(vertices, edges)
    return t


# --------------------------- mesh por edge -------------------------- #


def edge_spec_to_dict(spec: EdgeMeshSpec) -> Dict[str, Any]:
    return {
        "edge_id": spec.edge_id,
        "n_nodes": spec.n_nodes,
        "distribution": distribution_to_dict(spec.distribution),
    }


def edge_spec_from_dict(data: Dict[str, Any]) -> EdgeMeshSpec:
    return EdgeMeshSpec(
        int(data["edge_id"]),
        int(data["n_nodes"]),
        distribution_from_dict(data["distribution"]),
    )


# ------------------------------ blocks -------------------------------- #


def block_side_to_dict(side: BlockSide) -> Dict[str, Any]:
    return {
        "oriented_edges": [
            {"edge_id": oe.edge_id, "reversed": oe.reversed}
            for oe in side.oriented_edges
        ],
        "node_count": side.node_count,
    }


def block_side_from_dict(data: Dict[str, Any]) -> BlockSide:
    oriented = tuple(
        OrientedEdge(int(oe["edge_id"]), bool(oe.get("reversed", False)))
        for oe in data["oriented_edges"]
    )
    return BlockSide(oriented_edges=oriented, node_count=int(data.get("node_count", 0)))


def block_to_dict(block: Block) -> Dict[str, Any]:
    return {
        "id": block.id,
        "sides": [block_side_to_dict(s) for s in block.sides],
    }


def block_from_dict(data: Dict[str, Any]) -> Block:
    sides = tuple(block_side_from_dict(sd) for sd in data["sides"])
    if len(sides) != 4:
        raise ValueError(
            "Block {} does not have four sides in the file".format(data.get("id"))
        )
    return Block(int(data["id"]), sides)  # type: ignore[arg-type]


# ----------------------------- boundaries ----------------------------- #


def boundary_patch_to_dict(patch):
    """Serialize a BoundaryPatch without introducing Qt dependencies."""
    return {
        "id": patch.id,
        "name": patch.name,
        "type": patch.boundary_type.value,
        "edge_ids": list(patch.edge_ids),
    }


def boundary_patch_from_dict(data):
    from meshcad.core.boundary import BoundaryPatch, BoundaryType

    return BoundaryPatch(
        id=int(data["id"]),
        name=str(data["name"]),
        boundary_type=BoundaryType(data["type"]),
        edge_ids=tuple(int(edge_id) for edge_id in data.get("edge_ids", [])),
    )


def boundary_model_to_dict(model):
    return {
        "patches": [boundary_patch_to_dict(patch) for patch in model.patches()],
        "next_patch_id": model.next_patch_id,
        "periodic_pairs": [periodic_pair_to_dict(pair) for pair in model.periodic_pairs()],
        "next_periodic_pair_id": model.next_periodic_pair_id,
    }


def boundary_model_from_dict(data):
    from meshcad.core.boundary import BoundaryModel

    data = data or {}
    patches = [boundary_patch_from_dict(item) for item in data.get("patches", [])]
    pairs = [periodic_pair_from_dict(item) for item in data.get("periodic_pairs", [])]
    return BoundaryModel.restore(
        patches, data.get("next_patch_id"), pairs, data.get("next_periodic_pair_id")
    )


def periodic_pair_to_dict(pair):
    return {
        "id": pair.id,
        "name": pair.name,
        "source_patch_id": pair.source_patch_id,
        "target_patch_id": pair.target_patch_id,
        "reversed": pair.reversed,
        "tolerance": pair.tolerance,
        "transform": {
            "translation_x": pair.transform.translation_x,
            "translation_y": pair.transform.translation_y,
        },
    }


def periodic_pair_from_dict(data):
    from meshcad.core.boundary import PeriodicPair, PeriodicTransform
    transform = data.get("transform", {})
    return PeriodicPair(
        int(data["id"]), str(data["name"]),
        int(data["source_patch_id"]), int(data["target_patch_id"]),
        bool(data.get("reversed", False)), float(data.get("tolerance", 1.0e-8)),
        PeriodicTransform(float(transform.get("translation_x", 0.0)),
                          float(transform.get("translation_y", 0.0))),
    )
