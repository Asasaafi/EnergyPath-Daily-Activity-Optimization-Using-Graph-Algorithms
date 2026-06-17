"""
----------------
Bellman-Ford single-source shortest-path algorithm, implemented from
scratch on an explicit edge list.

This is Algorithm B in the EnergyPath comparison. Unlike Dijkstra,
Bellman-Ford tolerates negative edge weights and can *detect* negative
cycles (a property exploited here purely as a correctness/robustness
feature -- the EnergyPath domain itself only ever uses positive
weights, so no negative cycle should ever legitimately be reported).

Complexity (proved in README.md, Section "Complexity Analysis"):
    Time:  O(V * E)
    Space: O(V + E)

Optimization note: a standard "early termination" optimization is
included -- if a full pass over all edges performs zero relaxations,
the distances have already converged and the remaining passes (up to
V-1) are skipped. This does not change the worst-case O(V*E) bound
(an adversarial graph can still force all V-1 passes) but it
significantly speeds up the common case, including the sparse
random benchmark graphs used here.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

Edge = Tuple[int, int, float]

INF = float("inf")


@dataclass
class BellmanFordResult:
    """Container for everything the UI / benchmark code needs."""

    distance: float                     # total cost, INF if unreachable
    path: List[int]                       # node ids, source ... target
    runtime_seconds: float                 # wall-clock time for the search
    negative_cycle_detected: bool           # True if a negative cycle exists
    passes_used: int                          # diagnostic: relaxation passes run


def bellman_ford(
    num_nodes: int,
    edges: List[Edge],
    source: int,
    target: Optional[int] = None,
) -> BellmanFordResult:
    """Run Bellman-Ford from ``source`` over a graph with ``num_nodes``
    vertices (ids 0..num_nodes-1) and the given edge list.

    Args:
        num_nodes: number of vertices.
        edges: list of (u, v, weight) tuples. Weights MAY be negative;
            the function will detect (but not "fix") negative cycles.
        source: starting vertex id.
        target: if given, a path is reconstructed for this vertex.

    Returns:
        BellmanFordResult with distance, path, runtime, and a
        negative-cycle flag. If a negative cycle is detected that is
        reachable from ``source``, ``distance`` is reported as
        ``-inf`` and ``path`` is left empty, since "the" shortest
        path is undefined in that case.
    """
    start_time = time.perf_counter()

    dist: List[float] = [INF] * num_nodes
    prev: List[Optional[int]] = [None] * num_nodes
    dist[source] = 0.0

    # Local variable caching for speed (standard CPython micro-opt:
    # avoids repeated attribute/global lookups inside the hot loop).
    n = num_nodes
    passes_used = 0

    for i in range(n - 1):
        updated = False
        for u, v, w in edges:
            du = dist[u]
            if du == INF:
                continue
            nd = du + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                updated = True
        passes_used = i + 1
        if not updated:
            break  # converged early; no more relaxations possible

    negative_cycle_detected = False
    for u, v, w in edges:
        du = dist[u]
        if du == INF:
            continue
        if du + w < dist[v]:
            negative_cycle_detected = True
            break

    runtime = time.perf_counter() - start_time

    final_distance = dist[target] if target is not None else 0.0
    path: List[int] = []

    if negative_cycle_detected and target is not None and dist[target] < INF:
        # A negative cycle exists and is reachable; "the" shortest
        # path is not well-defined (cost is unbounded below).
        final_distance = float("-inf")
    elif target is not None and dist[target] < INF:
        path = _reconstruct_path(prev, source, target)

    return BellmanFordResult(
        distance=final_distance,
        path=path,
        runtime_seconds=runtime,
        negative_cycle_detected=negative_cycle_detected,
        passes_used=passes_used,
    )


def bellman_ford_all_distances(
    num_nodes: int, edges: List[Edge], source: int
) -> Tuple[List[float], float, bool]:
    """Convenience wrapper used by the benchmark suite: returns the
    full distance array, runtime, and negative-cycle flag."""
    start_time = time.perf_counter()
    dist: List[float] = [INF] * num_nodes
    dist[source] = 0.0

    for i in range(num_nodes - 1):
        updated = False
        for u, v, w in edges:
            du = dist[u]
            if du == INF:
                continue
            nd = du + w
            if nd < dist[v]:
                dist[v] = nd
                updated = True
        if not updated:
            break

    negative_cycle_detected = False
    for u, v, w in edges:
        du = dist[u]
        if du == INF:
            continue
        if du + w < dist[v]:
            negative_cycle_detected = True
            break

    runtime = time.perf_counter() - start_time
    return dist, runtime, negative_cycle_detected


def _reconstruct_path(prev: List[Optional[int]], source: int, target: int) -> List[int]:
    """Walk the predecessor array backwards from target to source."""
    path = [target]
    node = target
    visited = {target}
    while node != source:
        node = prev[node]
        if node is None or node in visited:
            return []  # unreachable or corrupted predecessor chain
        visited.add(node)
        path.append(node)
    path.reverse()
    return path
