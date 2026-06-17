"""
------------
Empirical performance benchmark for Dijkstra vs. Bellman-Ford.

For each graph size in ``DEFAULT_SIZES``, a reproducible random graph
is generated (``random.seed(42)``, threaded explicitly -- see
``graph_generator.generate_random_graph``), and both algorithms are
run ``DEFAULT_REPEATS`` times from node 0 to node (n-1). The mean
runtime of each algorithm at each size is written to
``results/runtime.csv``.

This file is runnable directly:

    python -m src.benchmark                # full spec: 100..10000, 5 reps
    python -m src.benchmark --quick         # smaller demo run (fast)
    python -m src.benchmark --sizes 100 500 --repeats 3

NOTE ON RUNTIME: Bellman-Ford is O(V*E). At n=10,000 with an average
out-degree of 4 (E ~= 40,000 edges), a single run touches on the order
of 10^8-10^9 elementary operations in pure Python. Five repeats at the
two largest sizes (5,000 and 10,000) can take from under a minute to
several minutes depending on the host machine -- this slow-down *is*
the expected, theoretically-predicted result (see README.md,
"Complexity Analysis"), not a bug. Use ``--quick`` for a fast sanity
check while iterating.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph_generator import generate_random_graph, edges_to_adjacency_list
from src.dijkstra import dijkstra_all_distances
from src.bellman_ford import bellman_ford_all_distances

DEFAULT_SIZES: List[int] = [100, 500, 1000, 5000, 10000]
DEFAULT_REPEATS: int = 5
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
RESULTS_CSV = os.path.join(RESULTS_DIR, "runtime.csv")


def run_benchmark(sizes: List[int], repeats: int, avg_out_degree: int = 4, verbose: bool = True) -> List[dict]:
    """Run the full benchmark suite and return a list of row dicts
    (also written to ``results/runtime.csv``)."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rows: List[dict] = []

    for n in sizes:
        num_nodes, edges = generate_random_graph(n, avg_out_degree=avg_out_degree, seed=42)
        adj = edges_to_adjacency_list(num_nodes, edges)
        source, target = 0, num_nodes - 1

        dij_times: List[float] = []
        bf_times: List[float] = []

        for rep in range(repeats):
            dist_d, t_d = dijkstra_all_distances(adj, source)
            dij_times.append(t_d)

            dist_b, t_b, neg_cycle = bellman_ford_all_distances(num_nodes, edges, source)
            bf_times.append(t_b)

            # Cross-check correctness on every repeat, every size.
            assert not neg_cycle, f"Unexpected negative cycle at n={n}"
            assert abs(dist_d[target] - dist_b[target]) < 1e-6, (
                f"Mismatch at n={n}: Dijkstra={dist_d[target]} "
                f"Bellman-Ford={dist_b[target]}"
            )

            if verbose:
                print(
                    f"  n={n:>6} rep={rep + 1}/{repeats}  "
                    f"Dijkstra={t_d * 1000:.3f}ms  Bellman-Ford={t_b * 1000:.3f}ms"
                )

        avg_dij = sum(dij_times) / repeats
        avg_bf = sum(bf_times) / repeats

        rows.append(
            {
                "num_nodes": n,
                "num_edges": len(edges),
                "dijkstra_avg_ms": avg_dij * 1000,
                "bellman_ford_avg_ms": avg_bf * 1000,
                "repeats": repeats,
            }
        )

        if verbose:
            print(
                f"n={n:>6} | edges={len(edges):>7} | "
                f"Dijkstra avg={avg_dij * 1000:8.3f} ms | "
                f"Bellman-Ford avg={avg_bf * 1000:10.3f} ms"
            )

    _write_csv(rows)
    return rows


def _write_csv(rows: List[dict]) -> None:
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["num_nodes", "num_edges", "dijkstra_avg_ms", "bellman_ford_avg_ms", "repeats"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"\nResults written to {RESULTS_CSV}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EnergyPath benchmark: Dijkstra vs Bellman-Ford")
    parser.add_argument(
        "--sizes", type=int, nargs="+", default=None,
        help=f"Graph sizes to benchmark (default: {DEFAULT_SIZES})",
    )
    parser.add_argument(
        "--repeats", type=int, default=None,
        help=f"Repeats per size (default: {DEFAULT_REPEATS})",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Fast demo run: sizes [100, 500, 1000], 3 repeats",
    )
    args = parser.parse_args()

    if args.quick:
        sizes = [100, 500, 1000]
        repeats = 3
    else:
        sizes = args.sizes or DEFAULT_SIZES
        repeats = args.repeats or DEFAULT_REPEATS

    print(f"Running benchmark: sizes={sizes}, repeats={repeats}\n")
    run_benchmark(sizes, repeats)


if __name__ == "__main__":
    main()
