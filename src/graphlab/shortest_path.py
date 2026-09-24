"""Four shortest-path algorithms, each answering a different question."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

from .graph import Graph, haversine

INFINITY = float("inf")


@dataclass
class PathResult:
    distances: dict[str, float]
    previous: dict[str, str]
    expanded: int = 0
    source: str = ""
    negative_cycle: bool = False
    relaxations: int = 0
    _path_cache: dict = field(default_factory=dict, repr=False)

    def path_to(self, target: str) -> list[str]:
        """Walk the predecessor chain back to the source."""
        if target not in self.distances or self.distances[target] == INFINITY:
            return []
        path = [target]
        while path[-1] != self.source:
            if path[-1] not in self.previous:
                return []
            path.append(self.previous[path[-1]])
        return list(reversed(path))

    def cost_to(self, target: str) -> float:
        return self.distances.get(target, INFINITY)


def dijkstra(graph: Graph, source: str, weight: str = "distance",
             target: str | None = None) -> PathResult:
    """Cheapest paths from one node, using a binary heap.

    A node can be pushed several times as better routes to it are found. Rather
    than decreasing a key in place, which a binary heap cannot do cheaply, stale
    entries are left in and skipped on the way out - the standard lazy-deletion
    trick that keeps the heap simple and the complexity at O(m log n).

    Requires non-negative weights: the algorithm settles a node the first time it
    is popped, which a negative edge could later undercut.
    """
    distances = {source: 0.0}
    previous: dict[str, str] = {}
    settled: set[str] = set()
    heap = [(0.0, source)]
    expanded = relaxations = 0

    while heap:
        cost, current = heapq.heappop(heap)
        if current in settled:
            continue  # a stale entry, superseded by a cheaper route
        settled.add(current)
        expanded += 1
        if target is not None and current == target:
            break
        for edge in graph.neighbours(current):
            relaxations += 1
            candidate = cost + edge.weight(weight)
            if candidate < distances.get(edge.target, INFINITY):
                distances[edge.target] = candidate
                previous[edge.target] = current
                heapq.heappush(heap, (candidate, edge.target))

    return PathResult(distances, previous, expanded, source, relaxations=relaxations)


def dijkstra_linear_scan(graph: Graph, source: str, weight: str = "distance") -> PathResult:
    """The same algorithm with the heap replaced by a linear scan.

    Kept because the difference is the point: O(n^2) against O(m log n). On a
    sparse street network that is the gap between usable and not, and
    `benchmark.py` measures it rather than asserting it.
    """
    distances = dict.fromkeys(graph.nodes, INFINITY)
    distances[source] = 0.0
    previous: dict[str, str] = {}
    unsettled = set(graph.nodes)
    expanded = 0

    while unsettled:
        current = min(unsettled, key=lambda node: distances[node])
        if distances[current] == INFINITY:
            break
        unsettled.remove(current)
        expanded += 1
        for edge in graph.neighbours(current):
            candidate = distances[current] + edge.weight(weight)
            if candidate < distances[edge.target]:
                distances[edge.target] = candidate
                previous[edge.target] = current

    return PathResult(distances, previous, expanded, source)


def a_star(graph: Graph, source: str, target: str, weight: str = "distance",
           max_speed_kmh: float = 50.0) -> PathResult:
    """Dijkstra steered by a guess at the distance remaining.

    The heuristic is the straight-line distance to the target (converted to
    seconds at the fastest speed in the network when routing on time). Both forms
    are admissible - they can never overestimate, since no road is shorter than
    the straight line and none is faster than the fastest road - which is what
    guarantees the answer is still optimal, not merely quick.
    """
    goal = graph.nodes[target]

    def heuristic(node_id: str) -> float:
        straight = haversine(graph.nodes[node_id], goal)
        if weight == "distance":
            return straight
        if weight == "time":
            return straight / (max_speed_kmh / 3.6)
        return 0.0  # no admissible hop-count heuristic without more structure

    distances = {source: 0.0}
    previous: dict[str, str] = {}
    settled: set[str] = set()
    heap = [(heuristic(source), 0.0, source)]
    expanded = 0

    while heap:
        _, cost, current = heapq.heappop(heap)
        if current in settled:
            continue
        settled.add(current)
        expanded += 1
        if current == target:
            break
        for edge in graph.neighbours(current):
            candidate = cost + edge.weight(weight)
            if candidate < distances.get(edge.target, INFINITY):
                distances[edge.target] = candidate
                previous[edge.target] = current
                heapq.heappush(heap, (candidate + heuristic(edge.target), candidate, edge.target))

    return PathResult(distances, previous, expanded, source)


def bellman_ford(graph: Graph, source: str, weight: str = "distance") -> PathResult:
    """Handles negative weights, and reports a negative cycle rather than looping.

    Relax every edge n-1 times: after k rounds every shortest path of k edges is
    correct. If an n-th round still improves something, a negative cycle is
    reachable and no shortest path exists, so the result says so instead of
    returning a number.
    """
    distances = dict.fromkeys(graph.nodes, INFINITY)
    distances[source] = 0.0
    previous: dict[str, str] = {}
    edges = list(graph.edges())
    relaxations = 0

    for _ in range(max(len(graph.nodes) - 1, 0)):
        changed = False
        for edge in edges:
            if distances[edge.source] == INFINITY:
                continue
            relaxations += 1
            candidate = distances[edge.source] + edge.weight(weight)
            if candidate < distances[edge.target] - 1e-12:
                distances[edge.target] = candidate
                previous[edge.target] = edge.source
                changed = True
        if not changed:
            break  # settled early: no further round can change anything

    for edge in edges:
        if distances[edge.source] != INFINITY and \
                distances[edge.source] + edge.weight(weight) < distances[edge.target] - 1e-12:
            return PathResult(distances, previous, 0, source, negative_cycle=True,
                              relaxations=relaxations)

    return PathResult(distances, previous, len(graph.nodes), source, relaxations=relaxations)


def path_cost(graph: Graph, path: list[str], weight: str) -> float:
    """Cost of an explicit route, for checking a path rather than trusting a number."""
    total = 0.0
    for a, b in zip(path, path[1:], strict=False):
        step = min((e.weight(weight) for e in graph.neighbours(a) if e.target == b), default=math.inf)
        total += step
    return total
