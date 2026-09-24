"""Searching a space too large to build: the 8-puzzle.

The sliding puzzle has 181,440 reachable states, which is small enough to explore
and large enough that the search strategy matters. The graph is never
constructed: states are generated as they are reached, which is the only way any
real state-space search works.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)  # 0 is the empty square
SIDE = 3


def neighbours(state: tuple[int, ...]) -> list[tuple[int, ...]]:
    """States reachable by sliding one tile into the empty square."""
    blank = state.index(0)
    row, col = divmod(blank, SIDE)
    out = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        r, c = row + dr, col + dc
        if not (0 <= r < SIDE and 0 <= c < SIDE):
            continue
        swap = r * SIDE + c
        tiles = list(state)
        tiles[blank], tiles[swap] = tiles[swap], tiles[blank]
        out.append(tuple(tiles))
    return out


def scramble(moves: int = 20, seed: int = 0) -> tuple[int, ...]:
    """Walk backwards from the goal, so the result is always solvable.

    Half of all arrangements of the tiles cannot be reached from the goal at all.
    Shuffling at random would produce unsolvable puzzles half the time and a
    search that runs until it has enumerated the entire component.
    """
    rng = random.Random(seed)
    state = GOAL
    for _ in range(moves):
        state = rng.choice(neighbours(state))
    return state


@dataclass
class SearchResult:
    path: list[tuple[int, ...]]
    expanded: int
    frontier_peak: int

    @property
    def moves(self) -> int:
        return max(len(self.path) - 1, 0)

    @property
    def solved(self) -> bool:
        return bool(self.path) and self.path[-1] == GOAL


def bfs_search(start: tuple[int, ...], goal: tuple[int, ...] = GOAL,
               limit: int = 400_000) -> SearchResult:
    """Breadth-first: guaranteed fewest moves, at the cost of holding the frontier."""
    if start == goal:
        return SearchResult([start], 0, 0)
    previous = {start: None}
    queue = deque([start])
    expanded, peak = 0, 1

    while queue and expanded < limit:
        current = queue.popleft()
        expanded += 1
        for nxt in neighbours(current):
            if nxt in previous:
                continue
            previous[nxt] = current
            if nxt == goal:
                return SearchResult(_rebuild(previous, nxt), expanded, peak)
            queue.append(nxt)
        peak = max(peak, len(queue))
    return SearchResult([], expanded, peak)


def bidirectional_bfs(start: tuple[int, ...], goal: tuple[int, ...] = GOAL,
                      limit: int = 400_000) -> SearchResult:
    """Search from both ends and meet in the middle.

    A breadth-first frontier grows like b^d. Two searches of depth d/2 cost
    2*b^(d/2), which for the same answer is the square root of the work. The
    saving is real but conditional: it needs the goal known in advance and moves
    that can be run backwards, which is why it is not the default everywhere.
    """
    if start == goal:
        return SearchResult([start], 0, 0)

    forward = {start: None}
    backward = {goal: None}
    front_queue, back_queue = deque([start]), deque([goal])
    expanded, peak = 0, 2

    while front_queue and back_queue and expanded < limit:
        # Always expand the smaller frontier: it keeps the two sides balanced.
        if len(front_queue) <= len(back_queue):
            queue, seen, other = front_queue, forward, backward
        else:
            queue, seen, other = back_queue, backward, forward

        for _ in range(len(queue)):
            current = queue.popleft()
            expanded += 1
            for nxt in neighbours(current):
                if nxt in seen:
                    continue
                seen[nxt] = current
                if nxt in other:
                    forward_part = _rebuild(forward, nxt)
                    backward_part = _rebuild(backward, nxt)
                    path = forward_part + list(reversed(backward_part[:-1]))
                    return SearchResult(path, expanded, peak)
                queue.append(nxt)
            peak = max(peak, len(front_queue) + len(back_queue))
    return SearchResult([], expanded, peak)


def _rebuild(previous: dict, node) -> list:
    path = [node]
    while previous[path[-1]] is not None:
        path.append(previous[path[-1]])
    return list(reversed(path))
