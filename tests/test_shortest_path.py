import networkx as nx
import pytest

from graphlab.city import generate_city, largest_component
from graphlab.graph import Edge, Graph, Node
from graphlab.shortest_path import (
    a_star,
    bellman_ford,
    dijkstra,
    dijkstra_linear_scan,
    path_cost,
)


@pytest.fixture(scope="module")
def city():
    return largest_component(generate_city(14, 14, seed=5))


def test_dijkstra_matches_networkx_everywhere(city):
    """The reference check: same distances as a library used by thousands."""
    source = next(iter(city.nodes))
    mine = dijkstra(city, source, "distance")
    reference = nx.single_source_dijkstra_path_length(city.to_networkx(), source, weight="length_m")
    for node, expected in reference.items():
        assert mine.cost_to(node) == pytest.approx(expected, rel=1e-9)


def test_heap_and_linear_scan_agree(city):
    """Two implementations of one algorithm must not disagree."""
    source = next(iter(city.nodes))
    heap = dijkstra(city, source, "time")
    linear = dijkstra_linear_scan(city, source, "time")
    for node in city.nodes:
        assert heap.cost_to(node) == pytest.approx(linear.cost_to(node), rel=1e-9)


def test_reconstructed_path_costs_what_the_algorithm_said(city):
    source, target = "0,0", "13,13"
    result = dijkstra(city, source, "distance")
    path = result.path_to(target)
    assert path[0] == source and path[-1] == target
    assert path_cost(city, path, "distance") == pytest.approx(result.cost_to(target), rel=1e-9)


def test_a_star_finds_the_same_route_while_expanding_fewer_nodes(city):
    source, target = "0,0", "13,13"
    exact = dijkstra(city, source, "distance", target=target)
    guided = a_star(city, source, target, "distance")
    assert guided.cost_to(target) == pytest.approx(exact.cost_to(target), rel=1e-9)
    assert guided.expanded <= exact.expanded


def test_a_star_on_travel_time_is_still_optimal(city):
    source, target = "0,0", "13,13"
    exact = dijkstra(city, source, "time", target=target)
    guided = a_star(city, source, target, "time", max_speed_kmh=50.0)
    assert guided.cost_to(target) == pytest.approx(exact.cost_to(target), rel=1e-9)


def test_bellman_ford_agrees_with_dijkstra_on_non_negative_weights(city):
    source = next(iter(city.nodes))
    slow = bellman_ford(city, source, "distance")
    fast = dijkstra(city, source, "distance")
    assert not slow.negative_cycle
    for node in city.nodes:
        assert slow.cost_to(node) == pytest.approx(fast.cost_to(node), rel=1e-9)


def negative_graph(with_cycle: bool) -> Graph:
    g = Graph()
    for name in "abc":
        g.add_node(Node(name, 52.0, 4.9))
    g.add_edge(Edge("a", "b", 1.0, 30.0), both_ways=False)
    g.add_edge(Edge("b", "c", -4.0, 30.0), both_ways=False)   # a discount, not a distance
    if with_cycle:
        g.add_edge(Edge("c", "a", 1.0, 30.0), both_ways=False)
    return g


def test_bellman_ford_handles_a_negative_edge():
    result = bellman_ford(negative_graph(with_cycle=False), "a", "distance")
    assert not result.negative_cycle
    assert result.cost_to("c") == pytest.approx(-3.0)


def test_bellman_ford_reports_a_negative_cycle_instead_of_looping():
    result = bellman_ford(negative_graph(with_cycle=True), "a", "distance")
    assert result.negative_cycle


def test_unreachable_nodes_are_reported_as_infinite_not_as_zero():
    g = Graph()
    g.add_node(Node("a", 52.0, 4.9))
    g.add_node(Node("island", 52.1, 4.9))
    result = dijkstra(g, "a", "distance")
    assert result.cost_to("island") == float("inf")
    assert result.path_to("island") == []


def test_early_exit_does_not_change_the_answer(city):
    source, target = "0,0", "7,9"
    full = dijkstra(city, source, "distance")
    stopped = dijkstra(city, source, "distance", target=target)
    assert stopped.cost_to(target) == pytest.approx(full.cost_to(target), rel=1e-12)
    assert stopped.expanded <= full.expanded
