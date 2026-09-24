import pytest

from graphlab.city import generate_city, largest_component
from graphlab.graph import Edge, Graph, Node, haversine
from graphlab.traversal import bfs, connected_components, dfs, find_cycle, topological_order


def line_graph(n=5, directed=True) -> Graph:
    g = Graph()
    for i in range(n):
        g.add_node(Node(f"n{i}", 52.0 + i * 0.001, 4.9))
    for i in range(n - 1):
        g.add_edge(Edge(f"n{i}", f"n{i+1}", 100.0, 30.0, f"street {i}"), both_ways=not directed)
    return g


def test_haversine_matches_a_known_distance():
    """Amsterdam to Rotterdam is about 57 km."""
    amsterdam = Node("a", 52.3676, 4.9041)
    rotterdam = Node("r", 51.9244, 4.4777)
    assert haversine(amsterdam, rotterdam) == pytest.approx(57_000, rel=0.05)
    assert haversine(amsterdam, amsterdam) == pytest.approx(0.0, abs=1e-9)


def test_edge_weights_are_consistent():
    edge = Edge("a", "b", length_m=1000.0, speed_kmh=36.0)
    assert edge.weight("hops") == 1.0
    assert edge.weight("distance") == 1000.0
    assert edge.travel_time_s == pytest.approx(100.0)  # 36 km/h = 10 m/s
    with pytest.raises(ValueError):
        edge.weight("nonsense")


def test_adding_an_edge_both_ways_creates_the_reverse():
    g = line_graph(3, directed=False)
    assert {e.target for e in g.neighbours("n1")} == {"n0", "n2"}


def test_bfs_returns_hop_distances_in_order():
    g = line_graph(5, directed=False)
    order, levels = bfs(g, "n0")
    assert order[0] == "n0"
    assert levels == {"n0": 0, "n1": 1, "n2": 2, "n3": 3, "n4": 4}


def test_dfs_visits_every_reachable_node_without_recursion_limits():
    g = line_graph(3000, directed=True)  # deep enough to blow a recursive implementation
    assert len(dfs(g, "n0")) == 3000


def test_connected_components_splits_a_disconnected_graph():
    g = line_graph(3, directed=False)
    g.add_node(Node("island", 52.4, 4.8))
    components = connected_components(g)
    assert sorted(len(c) for c in components) == [1, 3]


def test_find_cycle_returns_none_for_a_directed_acyclic_graph():
    assert find_cycle(line_graph(4, directed=True)) is None


def test_find_cycle_finds_one_when_it_exists():
    g = line_graph(4, directed=True)
    g.add_edge(Edge("n3", "n0", 10.0, 30.0), both_ways=False)
    cycle = find_cycle(g)
    assert cycle is not None
    assert len(cycle) >= 2


def test_a_diamond_is_not_a_cycle():
    """Two routes to the same node share a target without closing a loop.

    A visited-set implementation reports a cycle here; the three-colour one does not.
    """
    g = Graph()
    for name in "abcd":
        g.add_node(Node(name, 52.0, 4.9))
    for a, b in (("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")):
        g.add_edge(Edge(a, b, 1.0, 30.0), both_ways=False)
    assert find_cycle(g) is None


def test_topological_order_respects_every_edge():
    g = line_graph(5, directed=True)
    order = topological_order(g)
    position = {node: i for i, node in enumerate(order)}
    for edge in g.edges():
        assert position[edge.source] < position[edge.target]


def test_topological_order_refuses_a_cyclic_graph():
    g = line_graph(3, directed=True)
    g.add_edge(Edge("n2", "n0", 1.0, 30.0), both_ways=False)
    with pytest.raises(ValueError, match="cycle"):
        topological_order(g)


def test_generated_city_is_connected_after_pruning():
    city = largest_component(generate_city(12, 12, seed=1))
    assert len(connected_components(city)) == 1
    _, levels = bfs(city, next(iter(city.nodes)))
    assert len(levels) == city.n_nodes
