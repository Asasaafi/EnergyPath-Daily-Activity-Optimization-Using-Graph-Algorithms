"""
------
EnergyPath Streamlit application.

Lets a user pick a mood, a start activity, and a target activity, then
run Dijkstra, Bellman-Ford, or both (with a correctness cross-check)
over the EnergyPath activity graph. Also displays the offline
benchmark chart/table if ``results/runtime.csv`` and
``results/runtime_plot.png`` exist.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.graph_generator import ActivityGraph, Mood, MOOD_MULTIPLIERS
from src.dijkstra import dijkstra
from src.bellman_ford import bellman_ford

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
RUNTIME_CSV = os.path.join(RESULTS_DIR, "runtime.csv")
RUNTIME_PLOT = os.path.join(RESULTS_DIR, "runtime_plot.png")


@st.cache_resource
def load_graph() -> ActivityGraph:
    return ActivityGraph()


def path_names(graph: ActivityGraph, path_ids: list) -> list:
    return [graph.activity_name(i) for i in path_ids]


def main() -> None:
    st.set_page_config(page_title="EnergyPath", page_icon="🔋", layout="wide")
    graph = load_graph()

    st.title("🔋 EnergyPath")
    st.caption(
        "Find the lowest mental-energy path through your daily activities, "
        "using Dijkstra and Bellman-Ford -- implemented from scratch."
    )

    st.sidebar.header("Settings")
    mood_label = st.sidebar.radio(
        "How are you feeling today?",
        options=[m.value for m in Mood],
        index=1,
        help="Mood scales every transition's energy cost: "
             "Happy x1.0, Neutral x1.2, Tired x1.5.",
    )
    mood = Mood(mood_label)
    st.sidebar.markdown(f"**Multiplier:** ×{MOOD_MULTIPLIERS[mood]}")

    st.sidebar.divider()
    st.sidebar.markdown(
        "**Graph stats**\n\n"
        f"- Activities (vertices): {graph.num_nodes}\n"
        f"- Transitions (edges): {len(graph.base_edges)}"
    )

    col1, col2 = st.columns(2)
    with col1:
        start_name = st.selectbox("Start Activity", graph.activities, index=graph.activity_id("Wake Up"))
    with col2:
        target_name = st.selectbox("Target Activity", graph.activities, index=graph.activity_id("Sleep"))

    source = graph.activity_id(start_name)
    target = graph.activity_id(target_name)

    adj = graph.adjacency_list(mood)
    edges = graph.weighted_edges(mood)

    btn_col1, btn_col2, btn_col3 = st.columns(3)
    run_dijkstra = btn_col1.button("▶ Run Dijkstra", use_container_width=True)
    run_bf = btn_col2.button("▶ Run Bellman-Ford", use_container_width=True)
    run_compare = btn_col3.button("⚖ Compare Algorithms", use_container_width=True, type="primary")

    if source == target and (run_dijkstra or run_bf or run_compare):
        st.warning("Start and target activities are the same -- pick two different activities.")
        return

    if run_dijkstra:
        result = dijkstra(adj, source, target)
        _render_single_result("Dijkstra", graph, result.distance, result.path, result.runtime_seconds)

    if run_bf:
        result = bellman_ford(graph.num_nodes, edges, source, target)
        if result.negative_cycle_detected:
            st.error("Negative cycle detected -- no well-defined shortest path exists.")
        else:
            _render_single_result("Bellman-Ford", graph, result.distance, result.path, result.runtime_seconds)

    if run_compare:
        d_result = dijkstra(adj, source, target)
        b_result = bellman_ford(graph.num_nodes, edges, source, target)

        match = abs(d_result.distance - b_result.distance) < 1e-6

        st.subheader("Comparison Result")
        comp_df = pd.DataFrame(
            {
                "Algorithm": ["Dijkstra", "Bellman-Ford"],
                "Total Energy Cost": [round(d_result.distance, 3), round(b_result.distance, 3)],
                "Runtime (ms)": [
                    round(d_result.runtime_seconds * 1000, 4),
                    round(b_result.runtime_seconds * 1000, 4),
                ],
                "Path Length (hops)": [
                    max(len(d_result.path) - 1, 0),
                    max(len(b_result.path) - 1, 0),
                ],
            }
        )
        st.table(comp_df)

        if match:
            st.success(
                f"✅ Correctness check passed: both algorithms agree on "
                f"total energy cost = {d_result.distance:.3f}"
            )
        else:
            st.error(
                "❌ Mismatch between Dijkstra and Bellman-Ford results -- "
                "this should not happen on a positive-weight graph; please report this as a bug."
            )

        st.markdown("**Optimal Path (Dijkstra):**")
        st.write(" → ".join(path_names(graph, d_result.path)))
        st.markdown("**Optimal Path (Bellman-Ford):**")
        st.write(" → ".join(path_names(graph, b_result.path)))

    st.divider()
    st.subheader("📊 Offline Benchmark Results")
    st.caption(
        "Generated by `src/benchmark.py` on randomly generated graphs "
        "(random.seed(42), 5 repeats per size, mean runtime reported)."
    )

    if os.path.exists(RUNTIME_CSV):
        bench_df = pd.read_csv(RUNTIME_CSV)
        st.dataframe(bench_df, use_container_width=True)
    else:
        st.info("No benchmark results found yet. Run `python -m src.benchmark` to generate them.")

    if os.path.exists(RUNTIME_PLOT):
        st.image(RUNTIME_PLOT, caption="Runtime Comparison: Dijkstra vs. Bellman-Ford", use_container_width=True)
    else:
        st.info("No benchmark plot found yet. Run `python -m src.visualization` to generate it.")


def _render_single_result(algo_name: str, graph: ActivityGraph, distance: float, path: list, runtime_s: float) -> None:
    st.subheader(f"{algo_name} Result")
    if not path or distance == float("inf"):
        st.error(f"No path exists between the selected activities under {algo_name}.")
        return
    c1, c2 = st.columns(2)
    c1.metric("Total Energy Cost", f"{distance:.3f}")
    c2.metric("Runtime", f"{runtime_s * 1000:.4f} ms")
    st.markdown("**Optimal Path:**")
    st.write(" → ".join(path_names(graph, path)))


if __name__ == "__main__":
    main()
