"""A weighted directed graph, stored as adjacency lists.

Adjacency lists rather than a matrix because street networks are sparse: a
junction has three or four neighbours whatever the size of the city, so a matrix
would be 99.9% zeros and every traversal would spend its time reading them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class Node:
    id: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    length_m: float
    speed_kmh: float
    name: str = ""

    @property
    def travel_time_s(self) -> float:
        return self.length_m / (self.speed_kmh / 3.6)

    def weight(self, kind: str) -> float:
        """Three ways to measure the same street.

        The choice is the whole point of the routing section: minimising turns,
        metres and seconds give different routes through the same city.
        """
        if kind == "hops":
            return 1.0
        if kind == "distance":
            return self.length_m
        if kind == "time":
            return self.travel_time_s
        raise ValueError(f"unknown weight: {kind!r}")


def haversine(a: Node, b: Node) -> float:
    """Great-circle distance in metres between two coordinates."""
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


@dataclass
class Graph:
    nodes: dict[str, Node] = field(default_factory=dict)
    adjacency: dict[str, list[Edge]] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node
        self.adjacency.setdefault(node.id, [])

    def add_edge(self, edge: Edge, both_ways: bool = True) -> None:
        self.adjacency.setdefault(edge.source, []).append(edge)
        if both_ways:
            reverse = Edge(edge.target, edge.source, edge.length_m, edge.speed_kmh, edge.name)
            self.adjacency.setdefault(edge.target, []).append(reverse)

    def neighbours(self, node_id: str) -> list[Edge]:
        return self.adjacency.get(node_id, [])

    @property
    def n_nodes(self) -> int:
        return len(self.nodes)

    @property
    def n_edges(self) -> int:
        return sum(len(edges) for edges in self.adjacency.values())

    def edges(self):
        for edges in self.adjacency.values():
            yield from edges

    def to_networkx(self):
        """Only for the tests: the reference implementation to check against."""
        import networkx as nx

        G = nx.DiGraph()
        for node in self.nodes.values():
            G.add_node(node.id, lat=node.lat, lon=node.lon)
        for edge in self.edges():
            G.add_edge(edge.source, edge.target, length_m=edge.length_m,
                       time=edge.travel_time_s, hops=1.0, name=edge.name)
        return G
