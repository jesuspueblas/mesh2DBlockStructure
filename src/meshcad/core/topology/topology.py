"""Container of vertices and edges with unique identifiers."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from meshcad.core.geometry.arc import Arc
from meshcad.core.geometry.entity import GeometryEntity
from meshcad.core.geometry.line import Line
from meshcad.core.geometry.point import Point2D
from meshcad.core.geometry.spline import Spline, SplineSegment
from meshcad.core.topology.edge import Edge, OrientedEdge
from meshcad.core.topology.block_side import BlockSide
from meshcad.core.topology.vertex import Vertex

TOL = 1e-7


class Topology:
    def __init__(self) -> None:
        self._vertices: Dict[int, Vertex] = {}
        self._edges: Dict[int, Edge] = {}
        self._next_vertex_id = 0
        self._next_edge_id = 0

    def add_vertex(self, point: Point2D) -> Vertex:
        v = Vertex(self._next_vertex_id, point)
        self._next_vertex_id += 1
        self._vertices[v.id] = v
        return v

    def get_vertex(self, vertex_id: int) -> Vertex:
        return self._vertices[vertex_id]

    def has_vertex(self, vertex_id: int) -> bool:
        return vertex_id in self._vertices

    def vertices(self) -> List[Vertex]:
        return list(self._vertices.values())

    @property
    def next_edge_id(self) -> int:
        return self._next_edge_id

    def find_vertex_at(self, point: Point2D, tol: float = TOL) -> Optional[Vertex]:
        for v in self._vertices.values():
            if v.point.distance_to(point) <= tol:
                return v
        return None

    def add_edge(self, start_vertex: Vertex, end_vertex: Vertex,
                 geometry: GeometryEntity) -> Edge:
        if not self.has_vertex(start_vertex.id):
            raise ValueError("start_vertex does not belong to this topology")
        if not self.has_vertex(end_vertex.id):
            raise ValueError("end_vertex does not belong to this topology")
        if geometry.start_point().distance_to(start_vertex.point) > TOL:
            raise ValueError("The geometry start point does not match start_vertex")
        if geometry.end_point().distance_to(end_vertex.point) > TOL:
            raise ValueError("The geometry end point does not match end_vertex")
            
        e = Edge(self._next_edge_id, start_vertex.id, end_vertex.id, geometry)
        self._next_edge_id += 1
        self._edges[e.id] = e
        return e

    def get_edge(self, edge_id: int) -> Edge:
        return self._edges[edge_id]

    def has_edge(self, edge_id: int) -> bool:
        return edge_id in self._edges

    def edges(self) -> List[Edge]:
        return list(self._edges.values())

    def closest_point_on_edge(
        self, edge_id: int, point: Point2D
    ) -> Tuple[float, Point2D, float]:
        """Return the closest parameter, point, and distance on an edge."""
        geometry = self.get_edge(edge_id).geometry
        divisions = 256
        samples = [i / divisions for i in range(divisions + 1)]
        distances = [
            geometry.evaluate(t).distance_to(point) for t in samples
        ]
        best_index = min(range(len(distances)), key=distances.__getitem__)
        left = samples[max(0, best_index - 1)]
        right = samples[min(divisions, best_index + 1)]

        for _ in range(64):
            first = left + (right - left) / 3.0
            second = right - (right - left) / 3.0
            if geometry.evaluate(first).distance_to(point) <= geometry.evaluate(second).distance_to(point):
                right = second
            else:
                left = first

        parameter = (left + right) / 2.0
        closest = geometry.evaluate(parameter)
        return parameter, closest, closest.distance_to(point)

    @staticmethod
    def split_geometries(
        geometry: GeometryEntity, parameter: float
    ) -> Tuple[GeometryEntity, GeometryEntity]:
        if not math.isfinite(parameter) or not 0.0 < parameter < 1.0:
            raise ValueError("The split point must be strictly inside the edge.")

        point = geometry.evaluate(parameter)
        if isinstance(geometry, Line):
            first, second = Line(geometry.start, point), Line(point, geometry.end)
        elif isinstance(geometry, Arc):
            split_angle = geometry.start_angle + geometry.angle_span() * parameter
            first = Arc(
                geometry.center, geometry.radius,
                geometry.start_angle, split_angle,
            )
            second = Arc(
                geometry.center, geometry.radius,
                split_angle, geometry.end_angle,
            )
        elif isinstance(geometry, SplineSegment):
            split_t = geometry.start_t + (geometry.end_t - geometry.start_t) * parameter
            split_offset = Point2D(
                geometry.start_offset.x * (1.0 - parameter)
                + geometry.end_offset.x * parameter,
                geometry.start_offset.y * (1.0 - parameter)
                + geometry.end_offset.y * parameter,
            )
            first = SplineSegment(
                geometry.spline, geometry.start_t, split_t,
                geometry.start_offset, split_offset,
            )
            second = SplineSegment(
                geometry.spline, split_t, geometry.end_t,
                split_offset, geometry.end_offset,
            )
        elif isinstance(geometry, Spline):
            first = SplineSegment(geometry, 0.0, parameter)
            second = SplineSegment(geometry, parameter, 1.0)
        else:
            raise TypeError(
                "Unsupported edge geometry: {}".format(type(geometry).__name__)
            )

        if first.length() <= TOL or second.length() <= TOL:
            raise ValueError("The split point is too close to an edge endpoint.")
        return first, second

    def split_edge(self, edge_id: int, parameter: float) -> Tuple[Edge, Edge]:
        edge = self.get_edge(edge_id)
        first_geometry, second_geometry = self.split_geometries(edge.geometry, parameter)
        split_point = first_geometry.end_point()
        vertex = self.add_vertex(split_point)

        first_edge = Edge(
            edge.id, edge.start_vertex_id, vertex.id, first_geometry
        )
        self._edges[edge.id] = first_edge
        second_edge = self.add_edge(
            vertex,
            self.get_vertex(edge.end_vertex_id),
            second_geometry,
        )
        return first_edge, second_edge

    @staticmethod
    def replace_edge_in_side(
        side: BlockSide, edge_id: int, second_edge_id: int
    ) -> Tuple[OrientedEdge, ...]:
        """Replace an edge reference while retaining the side traversal."""
        replaced = []
        for oriented in side.oriented_edges:
            if oriented.edge_id != edge_id:
                replaced.append(oriented)
            elif oriented.reversed:
                replaced.extend((
                    OrientedEdge(second_edge_id, True),
                    OrientedEdge(edge_id, True),
                ))
            else:
                replaced.extend((
                    OrientedEdge(edge_id),
                    OrientedEdge(second_edge_id),
                ))
        return tuple(replaced)

    def remove_edge(self, edge_id: int) -> None:
        if edge_id not in self._edges:
            return
            
        edge = self._edges.pop(edge_id)
        
        # Remove vertices that are no longer connected to any edge.
        used_vertices = set()
        for e in self._edges.values():
            used_vertices.add(e.start_vertex_id)
            used_vertices.add(e.end_vertex_id)
            
        if edge.start_vertex_id not in used_vertices:
            self._vertices.pop(edge.start_vertex_id, None)
            
        if edge.end_vertex_id not in used_vertices:
            self._vertices.pop(edge.end_vertex_id, None)

    def move_vertex(self, vertex_id: int, new_point: Point2D) -> None:
        if vertex_id not in self._vertices:
            return
        self._vertices[vertex_id] = Vertex(vertex_id, new_point)

        for eid, edge in list(self._edges.items()):
            if edge.start_vertex_id == vertex_id or edge.end_vertex_id == vertex_id:
                g = edge.geometry
                v_start = self._vertices[edge.start_vertex_id].point
                v_end = self._vertices[edge.end_vertex_id].point

                if isinstance(g, Line):
                    new_g = Line(v_start, v_end)
                elif isinstance(g, Arc):
                    d = v_start.distance_to(v_end)
                    R = g.radius
                    if d > 2 * R:
                        R = d / 2.0
                    h = math.sqrt(max(0.0, R**2 - (d/2)**2))
                    mid = Point2D((v_start.x + v_end.x)/2, (v_start.y + v_end.y)/2)
                    dx, dy = v_end.x - v_start.x, v_end.y - v_start.y
                    nx, ny = -dy, dx
                    norm = math.hypot(nx, ny)
                    if norm > 1e-9:
                        nx, ny = nx/norm, ny/norm
                    else:
                        nx, ny = 0.0, 1.0
                    
                    c1 = Point2D(mid.x + h*nx, mid.y + h*ny)
                    c2 = Point2D(mid.x - h*nx, mid.y - h*ny)
                    new_center = c1 if g.center.distance_to(c1) < g.center.distance_to(c2) else c2
                    
                    a0 = math.atan2(v_start.y - new_center.y, v_start.x - new_center.x)
                    a1 = math.atan2(v_end.y - new_center.y, v_end.x - new_center.x)
                    new_g = Arc(new_center, R, a0, a1)
                elif isinstance(g, Spline):
                    pts = list(g.points)
                    if edge.start_vertex_id == vertex_id:
                        pts[0] = v_start
                    if edge.end_vertex_id == vertex_id:
                        pts[-1] = v_end
                    new_g = Spline(tuple(pts))
                elif isinstance(g, SplineSegment):
                    new_g = g.with_endpoints(v_start, v_end)
                else:
                    new_g = g

                self._edges[eid] = Edge(eid, edge.start_vertex_id, edge.end_vertex_id, new_g)

    def move_edge_grip(self, edge_id: int, grip_index: int, new_point: Point2D) -> None:
        edge = self._edges.get(edge_id)
        if not edge:
            return
        g = edge.geometry

        if isinstance(g, Arc) and grip_index == 0:
            v_start = self._vertices[edge.start_vertex_id].point
            v_end = self._vertices[edge.end_vertex_id].point
            
            mx = (v_start.x + v_end.x) / 2.0
            my = (v_start.y + v_end.y) / 2.0
            dx = v_end.x - v_start.x
            dy = v_end.y - v_start.y
            
            nx, ny = -dy, dx
            norm = math.hypot(nx, ny)
            if norm > 1e-9:
                nx /= norm
                ny /= norm
                t = (new_point.x - mx) * nx + (new_point.y - my) * ny
                new_center = Point2D(mx + t * nx, my + t * ny)
            else:
                new_center = new_point

            r = new_center.distance_to(v_start)
            a0 = math.atan2(v_start.y - new_center.y, v_start.x - new_center.x)
            a1 = math.atan2(v_end.y - new_center.y, v_end.x - new_center.x)
            
            new_g = Arc(new_center, max(r, 1e-6), a0, a1)
            self._edges[edge_id] = Edge(edge_id, edge.start_vertex_id, edge.end_vertex_id, new_g)
        elif isinstance(g, Spline):
            pts = list(g.points)
            pts[grip_index + 1] = new_point
            new_g = Spline(tuple(pts))
            self._edges[edge_id] = Edge(edge_id, edge.start_vertex_id, edge.end_vertex_id, new_g)
        elif isinstance(g, SplineSegment):
            new_g = g.with_grip(grip_index, new_point)
            self._edges[edge_id] = Edge(
                edge_id, edge.start_vertex_id, edge.end_vertex_id, new_g
            )

    def import_state(self, vertices: Dict[int, Vertex], edges: Dict[int, Edge]) -> None:
        self._vertices = dict(vertices)
        self._edges = dict(edges)
        max_v = max(self._vertices.keys(), default=-1)
        max_e = max(self._edges.keys(), default=-1)
        self._next_vertex_id = max_v + 1
        self._next_edge_id = max_e + 1

    def __len__(self) -> int:
        return len(self._vertices) + len(self._edges)
