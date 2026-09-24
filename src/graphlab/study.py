"""Run every experiment and write reports/.

Usage: python -m graphlab.study
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .benchmark import compare_dijkstra  # noqa: E402
from .centrality import betweenness_centrality, busiest_streets  # noqa: E402
from .city import generate_city, largest_component  # noqa: E402
from .shortest_path import a_star, dijkstra, path_cost  # noqa: E402
from .statespace import bfs_search, bidirectional_bfs, scramble  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "reports"
FIG_DIR = REPORT_DIR / "figures"
SEED = 0
SIDE = 24


def md_table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def routing_section(graph, source, target):
    """The same trip under three definitions of 'best'."""
    routes = {}
    for weight in ("hops", "distance", "time"):
        result = dijkstra(graph, source, weight)
        path = result.path_to(target)
        routes[weight] = {
            "path": path,
            "turns": len(path) - 1,
            "metres": path_cost(graph, path, "distance"),
            "seconds": path_cost(graph, path, "time"),
        }

    def shared(a, b):
        # strict=False: pairing a route with its own tail yields consecutive edges.
        ea = set(zip(routes[a]["path"], routes[a]["path"][1:], strict=False))
        eb = set(zip(routes[b]["path"], routes[b]["path"][1:], strict=False))
        return len(ea & eb) / max(len(ea | eb), 1)

    overlap = {f"{a} vs {b}": shared(a, b)
               for a, b in (("hops", "distance"), ("hops", "time"), ("distance", "time"))}

    fig, ax = plt.subplots(figsize=(6.5, 6))
    for edge in graph.edges():
        a, b = graph.nodes[edge.source], graph.nodes[edge.target]
        ax.plot([a.lon, b.lon], [a.lat, b.lat], color="#DDDDDD", lw=0.6, zorder=1)
    colours = {"hops": "#55A868", "distance": "#4C72B0", "time": "#C44E52"}
    for weight, route in routes.items():
        lons = [graph.nodes[n].lon for n in route["path"]]
        lats = [graph.nodes[n].lat for n in route["path"]]
        ax.plot(lons, lats, color=colours[weight], lw=2, alpha=0.75, label=weight, zorder=2)
    ax.set(xlabel="Longitude", ylabel="Latitude", title="Three definitions of the best route")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "routes.png", dpi=150)
    plt.close(fig)
    return routes, overlap


def search_section():
    """Bidirectional search against plain BFS on puzzles of rising difficulty."""
    rows = []
    for seed in (3, 11, 23, 47, 91):
        start = scramble(moves=120, seed=seed)
        plain = bfs_search(start)
        both = bidirectional_bfs(start)
        rows.append(
            {
                "seed": seed, "moves": plain.moves,
                "bfs_expanded": plain.expanded, "bidirectional_expanded": both.expanded,
                "agree": plain.moves == both.moves,
                "speedup": plain.expanded / max(both.expanded, 1),
            }
        )

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter([r["moves"] for r in rows], [r["bfs_expanded"] for r in rows],
               label="breadth-first", color="#4C72B0")
    ax.scatter([r["moves"] for r in rows], [r["bidirectional_expanded"] for r in rows],
               label="bidirectional", color="#55A868", marker="s")
    ax.set(xlabel="Optimal solution length (moves)", ylabel="States expanded",
           title="8-puzzle: meeting in the middle")
    ax.set_yscale("log")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "search.png", dpi=150)
    plt.close(fig)
    return rows


def run() -> dict:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    graph = largest_component(generate_city(SIDE, SIDE, seed=SEED))
    source, target = "0,0", f"{SIDE - 1},{SIDE - 1}"

    routes, overlap = routing_section(graph, source, target)

    star = a_star(graph, source, target, "distance")
    plain = dijkstra(graph, source, "distance", target=target)

    centrality = betweenness_centrality(graph, weight="distance")
    streets = busiest_streets(graph, centrality, top=8)

    benchmark = compare_dijkstra()
    searches = search_section()

    fig, ax = plt.subplots(figsize=(6, 4))
    nodes = [r["nodes"] for r in benchmark["rows"]]
    ax.loglog(nodes, [r["heap_seconds"] for r in benchmark["rows"]], "o-",
              label=f"binary heap (slope {benchmark['heap_exponent']:.2f})", color="#4C72B0")
    ax.loglog(nodes, [r["linear_seconds"] for r in benchmark["rows"]], "s-",
              label=f"linear scan (slope {benchmark['linear_exponent']:.2f})", color="#C44E52")
    ax.set(xlabel="Nodes", ylabel="Seconds", title="Dijkstra: the cost of the wrong data structure")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "benchmark.png", dpi=150)
    plt.close(fig)

    fastest, shortest = routes["time"], routes["distance"]
    lines = [
        "# Graph algorithms on a city",
        "",
        f"Generated {date.today().isoformat()} by `python -m graphlab.study`. "
        f"Graph: {graph.n_nodes} junctions, {graph.n_edges} directed street segments, "
        "generated (see `city.py`) because street extracts cannot be redistributed here.",
        "",
        "## 1. There is no such thing as the best route",
        "",
        md_table(
            ["Optimising", "Turns", "Metres", "Seconds"],
            [[weight, r["turns"], f"{r['metres']:,.0f}", f"{r['seconds']:,.0f}"]
             for weight, r in routes.items()],
        ),
        "",
        "![Routes](figures/routes.png)",
        "",
        f"The quickest route is {fastest['metres'] - shortest['metres']:,.0f} m longer than the "
        f"shortest one ({(fastest['metres'] / shortest['metres'] - 1) * 100:.1f}%) and arrives "
        f"{shortest['seconds'] - fastest['seconds']:,.0f} seconds sooner "
        f"({(1 - fastest['seconds'] / shortest['seconds']) * 100:.1f}% quicker). The routes share "
        f"only {overlap['distance vs time']:.0%} of their streets. Same graph, same pair of "
        "junctions, same algorithm - the answer is set entirely by what you put in the weight.",
        "",
        "## 2. A heuristic is free information",
        "",
        md_table(
            ["Algorithm", "Nodes expanded", "Route length (m)"],
            [
                ["Dijkstra", plain.expanded, f"{plain.cost_to(target):,.0f}"],
                ["A* with straight-line distance", star.expanded, f"{star.cost_to(target):,.0f}"],
            ],
        ),
        "",
        f"A* reaches the identical answer while expanding "
        f"{(1 - star.expanded / plain.expanded) * 100:.0f}% fewer nodes. The heuristic has to be "
        "admissible - never an overestimate - and the straight-line distance qualifies because no "
        "road is shorter than the straight line. Drop that property and A* gets faster still and "
        "stops being correct, which is the trade every routing engine has to decide on.",
        "",
        "## 3. Which streets does the city depend on?",
        "",
        "Betweenness centrality: the share of shortest paths that run through a junction. "
        "Brandes' algorithm computes it in O(nm + n² log n) rather than the O(n³) the definition "
        "suggests.",
        "",
        md_table(["Street", "Betweenness"], [[name, f"{value:.4f}"] for name, value in streets]),
        "",
        "These are not the longest streets or the fastest. They are the ones with no substitute: "
        "close one and traffic has nowhere equivalent to go.",
        "",
        "## 4. The data structure is the algorithm",
        "",
        md_table(
            ["Nodes", "Edges", "Binary heap (s)", "Linear scan (s)", "Ratio"],
            [[r["nodes"], r["edges"], f"{r['heap_seconds']:.4f}", f"{r['linear_seconds']:.4f}",
              f"{r['linear_seconds'] / r['heap_seconds']:.1f}x"] for r in benchmark["rows"]],
        ),
        "",
        "![Benchmark](figures/benchmark.png)",
        "",
        f"Fitted growth exponents: **{benchmark['heap_exponent']:.2f}** for the heap and "
        f"**{benchmark['linear_exponent']:.2f}** for the linear scan, against the O(m log n) and "
        "O(n²) the theory predicts on a sparse graph. Same algorithm, same answers; one line of "
        "difference in how the next node is chosen.",
        "",
        "## 5. Searching a space nobody built",
        "",
        "The 8-puzzle has 181,440 reachable states. They are generated as the search reaches "
        "them - the graph never exists in memory, which is the only way state-space search works "
        "at any real scale.",
        "",
        md_table(
            ["Optimal moves", "BFS states expanded", "Bidirectional", "Speed-up", "Same answer"],
            [[r["moves"], f"{r['bfs_expanded']:,}", f"{r['bidirectional_expanded']:,}",
              f"{r['speedup']:.1f}x", "yes" if r["agree"] else "NO"] for r in searches],
        ),
        "",
        "![Search](figures/search.png)",
        "",
        "A breadth-first frontier grows like b^d, so two searches of depth d/2 cost the square "
        "root of one search of depth d. Both return the same optimal move count on every puzzle "
        "here - the saving is in work, not in quality. It needs the goal known in advance and "
        "reversible moves, which is why it is not the default everywhere.",
        "",
        "## Limitations",
        "",
        "- The city is generated. Its structure is plausible and its geometry is real "
        "latitude and longitude, but it is not Amsterdam.",
        "- Timings come from one machine and one Python build; the exponents transfer, the "
        "seconds do not.",
        "- These implementations are for understanding: no arc flags, no contraction "
        "hierarchies, none of what a production routing engine does to answer in microseconds.",
    ]
    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "report.md").write_text("\n".join(lines))

    payload = {
        "routes": {k: {kk: vv for kk, vv in v.items() if kk != "path"} for k, v in routes.items()},
        "overlap": overlap,
        "a_star": {"expanded": star.expanded, "dijkstra_expanded": plain.expanded},
        "busiest_streets": streets,
        "benchmark": benchmark,
        "search": searches,
    }
    (REPORT_DIR / "metrics.json").write_text(json.dumps(payload, indent=2, default=float))
    return payload


if __name__ == "__main__":
    result = run()
    print(json.dumps({k: result[k] for k in ("routes", "overlap", "a_star", "search")},
                     indent=2, default=float))
