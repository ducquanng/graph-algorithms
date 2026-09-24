"""Betweenness centrality by Brandes' algorithm.

A street's betweenness is the share of shortest paths between other pairs that
run through it. High betweenness means traffic has no alternative - the streets
that carry a city are not the longest or the widest but the ones with no
substitute.

The naive definition suggests enumerating all pairs of shortest paths, which is
O(n^3) in time and O(n^2) in memory. Brandes' insight is that the dependency of a
source on each node can be accumulated in one backward sweep per source, giving
O(nm) for unweighted graphs and O(nm + n^2 log n) weighted - the difference
between minutes and never on a city-sized graph.
"""

from __future__ import annotations

import heapq
from collections import deque

from .graph import Graph

INFINITY = float("inf")


def betweenness_centrality(graph: Graph, weight: str | None = "distance",
                           normalised: bool = True) -> dict[str, float]:
    """Node betweenness. `weight=None` counts hops via BFS, which is much faster."""
    centrality = dict.fromkeys(graph.nodes, 0.0)

    for source in graph.nodes:
        if weight is None:
            stack, predecessors, sigma = _bfs_counts(graph, source)
        else:
            stack, predecessors, sigma = _dijkstra_counts(graph, source, weight)

        delta = dict.fromkeys(graph.nodes, 0.0)
        # Walk back from the furthest node: every node's dependency is complete
        # before it is used, which is what removes the cubic factor.
        while stack:
            w = stack.pop()
            for v in predecessors[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != source:
                centrality[w] += delta[w]

    if normalised and len(graph.nodes) > 2:
        scale = 1 / ((len(graph.nodes) - 1) * (len(graph.nodes) - 2))
        centrality = {node: value * scale for node, value in centrality.items()}
    return centrality


def _bfs_counts(graph: Graph, source: str):
    """Shortest-path counts by hop count."""
    predecessors: dict[str, list[str]] = {node: [] for node in graph.nodes}
    sigma = dict.fromkeys(graph.nodes, 0.0)
    distance = dict.fromkeys(graph.nodes, -1)
    sigma[source], distance[source] = 1.0, 0

    stack, queue = [], deque([source])
    while queue:
        v = queue.popleft()
        stack.append(v)
        for edge in graph.neighbours(v):
            w = edge.target
            if distance[w] < 0:
                distance[w] = distance[v] + 1
                queue.append(w)
            if distance[w] == distance[v] + 1:
                sigma[w] += sigma[v]
                predecessors[w].append(v)
    return stack, predecessors, sigma


def _dijkstra_counts(graph: Graph, source: str, weight: str):
    """Shortest-path counts by weight, with ties accumulating rather than replacing."""
    predecessors: dict[str, list[str]] = {node: [] for node in graph.nodes}
    sigma = dict.fromkeys(graph.nodes, 0.0)
    distance = dict.fromkeys(graph.nodes, INFINITY)
    sigma[source], distance[source] = 1.0, 0.0

    seen = {source: 0.0}
    settled: set[str] = set()
    stack: list[str] = []
    heap = [(0.0, source)]

    while heap:
        cost, v = heapq.heappop(heap)
        if v in settled:
            continue
        settled.add(v)
        stack.append(v)
        distance[v] = cost
        for edge in graph.neighbours(v):
            w = edge.target
            candidate = cost + edge.weight(weight)
            if w not in settled and candidate < seen.get(w, INFINITY) - 1e-12:
                seen[w] = candidate
                heapq.heappush(heap, (candidate, w))
                sigma[w] = sigma[v]
                predecessors[w] = [v]
            elif abs(candidate - seen.get(w, INFINITY)) <= 1e-12 and w not in settled:
                sigma[w] += sigma[v]
                predecessors[w].append(v)
    return stack, predecessors, sigma


def busiest_streets(graph: Graph, centrality: dict[str, float], top: int = 10):
    """Rank named streets by the betweenness of the junctions they connect."""
    scores: dict[str, float] = {}
    for edge in graph.edges():
        if not edge.name:
            continue
        value = (centrality.get(edge.source, 0.0) + centrality.get(edge.target, 0.0)) / 2
        scores[edge.name] = max(scores.get(edge.name, 0.0), value)
    return sorted(scores.items(), key=lambda kv: -kv[1])[:top]
