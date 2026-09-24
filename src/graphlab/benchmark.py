"""Measuring what the complexity claims predict.

A stated complexity is a claim about how runtime grows, and a claim can be
checked: run the algorithm at several sizes, fit a line through log(size)
against log(time), and read off the exponent.
"""

from __future__ import annotations

import time
from statistics import median

import numpy as np

from .city import generate_city, largest_component
from .shortest_path import dijkstra, dijkstra_linear_scan


def time_call(function, *args, repeats: int = 3, **kwargs) -> float:
    """Median of a few runs: the minimum flatters, the mean follows the worst outlier."""
    timings = []
    for _ in range(repeats):
        started = time.perf_counter()
        function(*args, **kwargs)
        timings.append(time.perf_counter() - started)
    return median(timings)


def fit_exponent(sizes, timings) -> float:
    """Slope of log(time) against log(size): the empirical growth exponent."""
    # strict=True: one timing per size, so a mismatch means the caller lost a result.
    usable = [(s, t) for s, t in zip(sizes, timings, strict=True) if t > 0]
    if len(usable) < 2:
        return float("nan")
    x = np.log(np.array([s for s, _ in usable], dtype=float))
    y = np.log(np.array([t for _, t in usable], dtype=float))
    return float(np.polyfit(x, y, 1)[0])


def compare_dijkstra(sides=(14, 20, 28, 38, 52, 70), seed: int = 0) -> dict:
    """Binary heap against linear scan on the same graphs.

    Expected: O(m log n) against O(n^2). On a sparse graph m is proportional to n,
    so the exponents should come out near 1 and near 2.

    The sizes start at a few hundred nodes on purpose. Below that the timings are
    dominated by interpreter overhead and the clock's own resolution, and the
    fitted exponent measures those instead of the algorithms.
    """
    rows = []
    for side in sides:
        graph = largest_component(generate_city(side, side, seed=seed))
        source = next(iter(graph.nodes))
        rows.append(
            {
                "side": side,
                "nodes": graph.n_nodes,
                "edges": graph.n_edges,
                "heap_seconds": time_call(dijkstra, graph, source, "distance"),
                "linear_seconds": time_call(dijkstra_linear_scan, graph, source, "distance"),
            }
        )
    nodes = [r["nodes"] for r in rows]
    return {
        "rows": rows,
        "heap_exponent": fit_exponent(nodes, [r["heap_seconds"] for r in rows]),
        "linear_exponent": fit_exponent(nodes, [r["linear_seconds"] for r in rows]),
    }
