"""A generated street network.

Real OpenStreetMap extracts cannot be redistributed with this repository and the
Overpass API is not always reachable, so the city is generated: a jittered grid
with a share of streets removed, a few fast arterial roads, and real latitude and
longitude so distances and the A* heuristic are genuine geography rather than
grid indices.
"""

from __future__ import annotations

import random

from .graph import Edge, Graph, Node, haversine

# Roughly central Amsterdam, so the coordinates and distances are plausible.
ORIGIN_LAT, ORIGIN_LON = 52.3676, 4.9041
BLOCK_M = 120.0

STREET_NAMES = [
    "Kade", "Gracht", "Straat", "Laan", "Plein", "Steeg", "Dijk", "Weg", "Singel", "Markt",
]


def _name(rng: random.Random, index: int) -> str:
    prefix = rng.choice(["Noord", "Zuid", "Oost", "West", "Nieuwe", "Oude"])
    return f"{prefix} {rng.choice(STREET_NAMES)} {index}"


def generate_city(rows: int = 20, cols: int = 20, seed: int = 0, missing_share: float = 0.12,
                  arterial_every: int = 5, diagonal_share: float = 0.05) -> Graph:
    """A grid city with irregularities, arterial roads, diagonals and dead ends.

    Three deliberate departures from a plain lattice, because a plain lattice
    makes the routing questions trivial - every monotone path between two corners
    has the same length, so the shortest route is not unique and comparing
    weightings measures nothing:

    * blocks vary in size, so two routes of equal hop count differ in metres
    * every `arterial_every`-th row and column runs at 50 km/h against 30
    * a few diagonal avenues cut corners, as in most cities that grew rather than
      being planned

    Together these make the fewest-turns, shortest and quickest routes genuinely
    different, which is what the study measures.
    """
    rng = random.Random(seed)
    graph = Graph()

    metres_per_degree_lat = 111_320.0
    metres_per_degree_lon = 68_000.0  # at this latitude

    # Uneven block sizes: a cumulative walk rather than a fixed step.
    row_offsets = [0.0]
    for _ in range(rows - 1):
        row_offsets.append(row_offsets[-1] + rng.uniform(0.55, 1.6) * BLOCK_M)
    col_offsets = [0.0]
    for _ in range(cols - 1):
        col_offsets.append(col_offsets[-1] + rng.uniform(0.55, 1.6) * BLOCK_M)

    for r in range(rows):
        for c in range(cols):
            graph.add_node(
                Node(
                    id=f"{r},{c}",
                    lat=ORIGIN_LAT + (row_offsets[r] + rng.uniform(-15, 15)) / metres_per_degree_lat,
                    lon=ORIGIN_LON + (col_offsets[c] + rng.uniform(-15, 15)) / metres_per_degree_lon,
                )
            )

    index = 0
    for r in range(rows):
        for c in range(cols):
            here = graph.nodes[f"{r},{c}"]
            steps = [(0, 1), (1, 0)]
            if rng.random() < diagonal_share:
                steps.append((1, 1))
            for dr, dc in steps:
                nr, nc = r + dr, c + dc
                if nr >= rows or nc >= cols:
                    continue
                diagonal = dr == 1 and dc == 1
                if not diagonal and rng.random() < missing_share:
                    continue  # a canal, a park, a building: not every block connects
                there = graph.nodes[f"{nr},{nc}"]
                arterial = diagonal or (r % arterial_every == 0 and dr == 0) \
                    or (c % arterial_every == 0 and dc == 1)
                index += 1
                graph.add_edge(
                    Edge(
                        source=here.id,
                        target=there.id,
                        length_m=haversine(here, there),
                        speed_kmh=50.0 if arterial else 30.0,
                        name=_name(rng, index),
                    )
                )
    return graph


def largest_component(graph: Graph) -> Graph:
    """Keep the biggest connected piece, so every pair of nodes has a route.

    Removing streets can strand a corner of the grid. Reporting 'no path' for
    those would measure the generator rather than the algorithms.
    """
    from .traversal import connected_components

    components = connected_components(graph)
    keep = set(max(components, key=len))
    pruned = Graph()
    for node_id in keep:
        pruned.add_node(graph.nodes[node_id])
    for edge in graph.edges():
        if edge.source in keep and edge.target in keep:
            pruned.adjacency.setdefault(edge.source, []).append(edge)
    return pruned
