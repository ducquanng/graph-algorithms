import networkx as nx
import pytest

from graphlab.centrality import betweenness_centrality, busiest_streets
from graphlab.city import generate_city, largest_component
from graphlab.graph import Edge, Graph, Node
from graphlab.statespace import GOAL, bfs_search, bidirectional_bfs, neighbours, scramble


@pytest.fixture(scope="module")
def city():
    return largest_component(generate_city(9, 9, seed=7))


def test_betweenness_matches_networkx_unweighted(city):
    mine = betweenness_centrality(city, weight=None)
    reference = nx.betweenness_centrality(city.to_networkx(), normalized=True)
    for node, expected in reference.items():
        assert mine[node] == pytest.approx(expected, abs=1e-9)


def test_betweenness_matches_networkx_weighted(city):
    mine = betweenness_centrality(city, weight="distance")
    reference = nx.betweenness_centrality(city.to_networkx(), weight="length_m", normalized=True)
    for node, expected in reference.items():
        assert mine[node] == pytest.approx(expected, abs=1e-9)


def test_the_bridge_node_of_a_barbell_has_the_highest_betweenness():
    """Every path between the two halves runs through the middle."""
    g = Graph()
    for name in ["l1", "l2", "mid", "r1", "r2"]:
        g.add_node(Node(name, 52.0, 4.9))
    for a, b in (("l1", "l2"), ("l1", "mid"), ("l2", "mid"), ("mid", "r1"), ("mid", "r2"), ("r1", "r2")):
        g.add_edge(Edge(a, b, 1.0, 30.0))
    centrality = betweenness_centrality(g, weight=None)
    assert centrality["mid"] == max(centrality.values())
    assert centrality["mid"] > 0


def test_busiest_streets_returns_named_streets_in_order(city):
    centrality = betweenness_centrality(city, weight=None)
    streets = busiest_streets(city, centrality, top=5)
    assert len(streets) == 5
    assert [value for _, value in streets] == sorted((v for _, v in streets), reverse=True)


def test_puzzle_moves_depend_on_where_the_blank_is():
    centre = (1, 2, 3, 4, 0, 5, 6, 7, 8)
    corner = (0, 1, 2, 3, 4, 5, 6, 7, 8)
    edge = (1, 0, 2, 3, 4, 5, 6, 7, 8)
    assert len(neighbours(centre)) == 4
    assert len(neighbours(corner)) == 2
    assert len(neighbours(edge)) == 3


def test_every_move_is_reversible():
    state = scramble(10, seed=1)
    for nxt in neighbours(state):
        assert state in neighbours(nxt)


def test_scrambles_are_always_solvable():
    """Built by walking back from the goal, so the search can never fail."""
    for seed in range(5):
        assert bfs_search(scramble(30, seed=seed)).solved


def test_solving_the_goal_takes_no_moves():
    result = bfs_search(GOAL)
    assert result.moves == 0 and result.expanded == 0


def test_bfs_finds_the_optimal_length_for_a_known_scramble():
    """Three moves away from the goal, so the answer cannot be shorter."""
    state = GOAL
    for _ in range(3):
        state = neighbours(state)[0]
    assert bfs_search(state).moves <= 3


def test_bidirectional_search_agrees_with_bfs_and_expands_less():
    for seed in (2, 5, 9):
        start = scramble(60, seed=seed)
        plain, both = bfs_search(start), bidirectional_bfs(start)
        assert both.moves == plain.moves
        assert both.expanded <= plain.expanded


def test_returned_path_is_a_legal_sequence_of_moves():
    result = bidirectional_bfs(scramble(40, seed=3))
    assert result.path[-1] == GOAL
    for current, nxt in zip(result.path, result.path[1:], strict=False):
        assert nxt in neighbours(current)
