"""
-----------------
Reads ``results/runtime.csv`` (produced by ``benchmark.py``) and
renders a runtime-comparison chart: number of nodes (X) vs. average
runtime in milliseconds (Y), one line per algorithm.

Saves the chart to ``results/runtime_plot.png``.

Runnable directly:
    python -m src.visualization
"""

from __future__ import annotations

import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
RESULTS_CSV = os.path.join(RESULTS_DIR, "runtime.csv")
PLOT_PATH = os.path.join(RESULTS_DIR, "runtime_plot.png")


def load_results(csv_path: str = RESULTS_CSV):
    """Load the benchmark CSV into parallel lists."""
    sizes, dij_ms, bf_ms = [], [], []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sizes.append(int(row["num_nodes"]))
            dij_ms.append(float(row["dijkstra_avg_ms"]))
            bf_ms.append(float(row["bellman_ford_avg_ms"]))
    return sizes, dij_ms, bf_ms


def plot_runtime_comparison(csv_path: str = RESULTS_CSV, output_path: str = PLOT_PATH) -> str:
    """Generate and save the runtime-comparison line chart.

    Returns the path to the saved PNG.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"{csv_path} not found. Run `python -m src.benchmark` first."
        )

    sizes, dij_ms, bf_ms = load_results(csv_path)

    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=150)

    ax.plot(sizes, dij_ms, marker="o", linewidth=2, color="#2563eb", label="Dijkstra  O((V+E) log V)")
    ax.plot(sizes, bf_ms, marker="s", linewidth=2, color="#dc2626", label="Bellman-Ford  O(V·E)")

    ax.set_xlabel("Number of Nodes (V)", fontsize=11)
    ax.set_ylabel("Average Runtime (ms)", fontsize=11)
    ax.set_title("EnergyPath: Runtime Comparison\nDijkstra vs. Bellman-Ford", fontsize=13, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)

    for x, y in zip(sizes, dij_ms):
        ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8, color="#2563eb")
    for x, y in zip(sizes, bf_ms):
        ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0, -14), fontsize=8, color="#dc2626")

    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)

    print(f"Plot saved to {output_path}")
    return output_path


if __name__ == "__main__":
    plot_runtime_comparison()
