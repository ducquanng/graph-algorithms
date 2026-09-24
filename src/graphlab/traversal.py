"""Breadth-first and depth-first search, and what each one is for.

BFS visits in order of hop count, so it finds the fewest-edge path and nothing
else does that as cheaply. DFS goes deep first, which is what makes it the basis
for cycle detection and topological order.
"""

from __future__ import annotations

from collections import deque

from .graph import Graph


def bfs(graph: Graph, start: str):
    """Visit order and hop distance from `start`."""
    seen = {start: 0}
    order = [start]
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for edge in graph.neighbours(current):
            if edge.target not in seen:
                seen[edge.target] = seen[current] + 1
                order.append(edge.target)
                queue.append(edge.target)
    return order, seen


def dfs(graph: Graph, start: str) -> list[str]:
    """Iterative rather than recursive.

    A recursive DFS on a city graph of any size hits Python's recursion limit and
    dies; an explicit stack does not. The visit order differs from the textbook
    recursion because neighbours are pushed in order and popped in reverse.
    """
    seen = set()
    order = []
    stack = [start]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        order.append(current)
        for edge in reversed(graph.neighbours(current)):
            if edge.target not in seen:
                stack.append(edge.target)
    return order


def connected_components(graph: Graph) -> list[set[str]]:
    """Weakly connected components, treating every edge as undirected."""
    undirected: dict[str, set[str]] = {node: set() for node in graph.nodes}
    for edge in graph.edges():
        undirected[edge.source].add(edge.target)
        undirected.setdefault(edge.target, set()).add(edge.source)

    seen: set[str] = set()
    components = []
    for node in graph.nodes:
        if node in seen:
            continue
        stack, component = [node], set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(n for n in undirected[current] if n not in component)
        seen |= component
        components.append(component)
    return components


WHITE, GREY, BLACK = 0, 1, 2


def find_cycle(graph: Graph) -> list[str] | None:
    """Return a directed cycle if one exists, else None.

    Three colours, not a visited set: white unseen, grey on the current path,
    black finished. An edge to a grey node closes a cycle; an edge to a black one
    is just a second route to somewhere already settled. A plain visited set
    cannot tell those apart and reports cycles that are not there.
    """
    colour = dict.fromkeys(graph.nodes, WHITE)
    parent: dict[str, str | None] = {}

    for root in graph.nodes:
        if colour[root] != WHITE:
            continue
        stack = [(root, iter(graph.neighbours(root)))]
        colour[root] = GREY
        parent[root] = None
        while stack:
            current, edges = stack[-1]
            advanced = False
            for edge in edges:
                target = edge.target
                if colour.get(target, WHITE) == WHITE:
                    colour[target] = GREY
                    parent[target] = current
                    stack.append((target, iter(graph.neighbours(target))))
                    advanced = True
                    break
                if colour[target] == GREY:
                    cycle = [target, current]
                    walker = parent.get(current)
                    while walker is not None and walker != target:
                        cycle.append(walker)
                        walker = parent.get(walker)
                    return list(reversed(cycle))
            if not advanced:
                colour[current] = BLACK
                stack.pop()
    return None


def topological_order(graph: Graph) -> list[str]:
    """Kahn's algorithm: repeatedly take a node nothing depends on.

    Raises when a cycle exists, because a cyclic graph has no valid order and
    returning a partial one would hide the problem.
    """
    indegree = dict.fromkeys(graph.nodes, 0)
    for edge in graph.edges():
        indegree[edge.target] = indegree.get(edge.target, 0) + 1

    queue = deque(sorted(node for node, degree in indegree.items() if degree == 0))
    order = []
    while queue:
        current = queue.popleft()
        order.append(current)
        for edge in graph.neighbours(current):
            indegree[edge.target] -= 1
            if indegree[edge.target] == 0:
                queue.append(edge.target)
    if len(order) != len(graph.nodes):
        raise ValueError("graph contains a cycle, so it has no topological order")
    return order
