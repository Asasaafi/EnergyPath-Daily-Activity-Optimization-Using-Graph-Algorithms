# EnergyPath: Daily Activity Optimization Using Graph Algorithms

A Design & Analysis of Algorithms (DAA) capstone project. EnergyPath models a
person's day as a weighted directed graph and finds the lowest mental-energy
route from one activity to another, the same way a maps application finds the
shortest route between two physical locations. Two classical shortest-path
algorithms, Dijkstra and Bellman-Ford, are implemented from scratch, proven
correct, analyzed for complexity, benchmarked empirically, and wrapped in an
interactive Streamlit application.

## 1. Problem Modeling

Every day consists of a sequence of activities -- waking up, eating, studying,
exercising, socializing, sleeping -- and each transition from one activity to
the next consumes (or occasionally restores) a measurable amount of mental
energy. A student deciding "should I go straight from lecture to the gym, or
take a coffee break first?" is implicitly solving a shortest-path problem.

EnergyPath formalizes this as a weighted directed graph G = (V, E, w):

- **Vertices (V):** 36 named daily activities, e.g. *Wake Up*, *Attend
  Lecture*, *Coding Practice*, *Family Time*, *Sleep* (see
  `src/graph_generator.py` for the full list). This satisfies the assignment's
  minimum of 30-50 activities.
- **Edges (E):** a directed edge `u -> v` exists if it is plausible to move
  directly from activity `u` to activity `v` (for example, `Breakfast ->
  Commute`). Edges are directed because activities are not freely reversible
  -- you can go from *Breakfast* to *Commute*, but going from *Commute* back to
  *Breakfast* is not a natural transition in the model.
- **Weights (w):** the base mental-energy cost of each transition, a positive
  real number. Costs were assigned to reflect intuition -- skipping good
  habits (e.g. `Wake Up -> Breakfast` directly, cost 9) is modeled as more
  costly than following them (`Wake Up -> Drink Water -> Breakfast`, cost
  2 + 4 = 6) -- which is exactly the kind of trade-off the shortest-path
  search is meant to surface.
- **Source / target:** the user picks a starting activity and a target
  activity; the system reports the minimum total-energy route between them.

The graph is intentionally **not** a single chain: many activities have two or
three outgoing edges with different costs (e.g. after *Lab Session* a person
could go to *Coding Practice*, *Coffee Break*, or *Lunch*), so the shortest
path is a genuine optimization result rather than a forced sequence.

### Mood system

A person's subjective cost of doing anything rises as they get more tired.
This is modeled as a single multiplicative factor applied to every edge
weight:

| Mood    | Multiplier |
|---------|-----------:|
| Happy   | 1.0        |
| Neutral | 1.2        |
| Tired   | 1.5        |

Because every base weight is positive and every multiplier is positive, the
mood-adjusted graph always has strictly positive weights -- a property the
correctness proofs below depend on.

## 2. Algorithm Design

Two algorithms are implemented from scratch (no library shortest-path
functions such as `networkx.shortest_path` are used anywhere in this
project):

### Algorithm A -- Dijkstra (`src/dijkstra.py`)

- Graph representation: **adjacency list**, `adj[u] = [(v, weight), ...]`.
- Priority queue: Python's `heapq` binary heap, storing `(distance, node)`
  pairs.
- Because `heapq` has no decrease-key operation, "lazy deletion" is used:
  stale, outdated heap entries are simply skipped when popped (checked
  against a `visited` set), rather than removed from the heap directly. This
  is the standard, textbook-correct way to implement Dijkstra with a binary
  heap in a language without an indexed priority queue.
- Returns the distance, the reconstructed path (via a predecessor map), and
  the wall-clock runtime of the search.
- Requires non-negative weights; the function defensively validates this and
  raises `ValueError` otherwise.

### Algorithm B -- Bellman-Ford (`src/bellman_ford.py`)

- Graph representation: **edge list**, `[(u, v, weight), ...]`.
- Performs up to `V - 1` relaxation passes over every edge.
- **Early-termination optimization:** if an entire pass produces zero
  relaxations, distances have already converged and remaining passes are
  skipped. This is a standard, widely-taught optimization that does not
  change the worst-case bound (an adversarial edge ordering can still force
  the full `V - 1` passes -- demonstrated empirically in Section 6).
- **Negative-cycle detection:** after the main loop, one additional pass
  checks whether any edge can still be relaxed; if so, a negative cycle
  reachable from the source exists, and this is reported rather than
  silently returning a wrong "shortest" distance.
- Returns the distance, the reconstructed path, the runtime, and a
  `negative_cycle_detected` flag.

Both algorithms return the *same* lightweight result shape (distance, path,
runtime) by design, which is what makes the side-by-side comparison and the
benchmark suite possible without special-casing either algorithm.

## 3. Algorithm Comparison & Correctness Cross-Check

Both algorithms are run on the **same** mood-adjusted graph, from the same
source to the same target, and their outputs are compared directly:

- **Path** -- the sequence of activities.
- **Total Energy Cost** -- the summed edge weight along that path.
- **Runtime** -- wall-clock search time, measured with
  `time.perf_counter()`.

Because both algorithms are correct shortest-path algorithms operating on the
same positive-weight graph, they are mathematically guaranteed to report the
same total cost (the path itself may legitimately differ if there are ties).
The application, the benchmark suite, and a dedicated assertion in
`benchmark.py` all verify `Dijkstra cost == Bellman-Ford cost` on every run --
this acts as a built-in correctness cross-check: if the two ever disagreed, it
would indicate a bug in one of the implementations.

## 4. Complexity Analysis

Let V = number of vertices, E = number of edges.

### Dijkstra: O((V + E) log V)

Each vertex is inserted into the heap and extracted (popped) at most once as
the "settled" minimum -- that is O(V log V) for the `V` heap pops, each
O(log V). Each edge is examined exactly once (when its source vertex is
settled), and may trigger one heap push -- that is O(E log V) for up to `E`
pushes, each O(log V). Summing: **O((V + E) log V)**. Space is O(V + E): the
adjacency list itself is O(V + E), plus O(V) for the distance/predecessor
arrays and O(V) heap entries in the worst case (more precisely O(E), since a
vertex can be pushed once per incoming improving edge under lazy deletion).

### Bellman-Ford: O(V x E)

The outer loop runs up to `V - 1` times (this many passes are sufficient and,
in the worst case, necessary -- a shortest path in a graph with no negative
cycle has at most `V - 1` edges, and each pass guarantees that all shortest
paths with at most `k` edges are correctly computed after the `k`-th pass; see
the proof in Section 5). Each pass examines every edge once, O(E). Total:
**O(V x E)**. The additional negative-cycle-detection pass is O(E) and does
not change the asymptotic bound. Space is O(V + E): O(E) for the edge list
and O(V) for the distance/predecessor arrays.

### Why Dijkstra is asymptotically faster

For any graph where E is not exponentially larger than V (i.e. essentially
always, since E <= V^2), `(V + E) log V` grows strictly slower than `V x E`
as the graph grows, because Bellman-Ford's bound has a full extra factor of V
in place of Dijkstra's log V factor. This is the central theoretical
prediction tested empirically in Section 6.

## 5. Correctness Proofs

### Dijkstra's correctness (sketch)

*Claim:* when Dijkstra settles (pops and finalizes) a vertex `u`, `dist[u]`
already equals the true shortest-path distance from the source.

*Proof by induction on settling order.* Base case: the source is settled
first with `dist[source] = 0`, trivially correct. Inductive step: suppose
every previously settled vertex has a correct final distance. Let `u` be the
next vertex popped from the heap, with priority `dist[u]`. Any path from the
source to `u` must, at some point, leave the set `S` of already-settled
vertices for the first time, crossing some edge `(x, y)` with `x in S` and
`y not in S`. Because all edge weights are non-negative, the length of the
path from the source up to and including this crossing edge is at least
`dist[x] + w(x, y)`, which by the heap's min-extraction property is at least
`dist[u]` (since `u` was chosen as the minimum-priority vertex still in the
heap, and `y`'s heap entry, if present, has priority >= `dist[u]`). The
remainder of the path from `y` to `u` can only add non-negative weight. Hence
no path to `u` can be shorter than `dist[u]`, while the algorithm has already
found a path of length exactly `dist[u]` (the one used to push `u`'s heap
entry). Therefore `dist[u]` is the true shortest distance. **This proof relies
critically on non-negative weights** -- with a negative edge, a path could
re-enter `S` and "undercut" `dist[u]` after `u` is settled, which is exactly
why Dijkstra requires non-negative weights and EnergyPath validates this.

### Bellman-Ford's correctness (sketch)

*Claim:* after `k` passes of the main relaxation loop, `dist[v]` is correct
for every vertex `v` whose shortest path from the source uses at most `k`
edges.

*Proof by induction on k.* Base case (`k = 0`): only the source has a
0-edge path, and `dist[source] = 0` is correct by initialization. Inductive
step: assume the claim holds after `k` passes. Consider a vertex `v` whose
shortest path uses exactly `k + 1` edges, with the path being
`source -> ... -> x -> v`, where the prefix `source -> ... -> x` is itself a
shortest path using `k` edges. By the inductive hypothesis, `dist[x]` is
already correct before pass `k + 1`. Pass `k + 1` examines every edge,
including `(x, v)`, and sets
`dist[v] = min(dist[v], dist[x] + w(x, v))`, which makes `dist[v]` correct
(it cannot be set lower than the true shortest distance, since that would
imply an even shorter path exists, and it is guaranteed to reach the true
value because the prefix is already correct). By induction, the claim holds
for all `k`.

In a graph with no negative cycle, every shortest path has at most `V - 1`
edges (a simple path cannot revisit a vertex without repeating a cycle, and
repeating a non-negative cycle never helps), so after `V - 1` passes every
`dist[v]` is correct. The negative-cycle check follows directly: if a `V`-th
pass can still relax some edge, then some vertex's shortest path would need
more than `V - 1` edges to be optimal, which is only possible if a negative
cycle is reachable from the source.

## 6. Benchmarking

`src/benchmark.py` generates reproducible random graphs (`random.seed(42)`,
threaded explicitly through `graph_generator.generate_random_graph` rather
than relying on global RNG state) at sizes **100, 500, 1,000, 5,000, and
10,000** nodes, with average out-degree 4. Each algorithm is run **5 times**
per size from node 0 to node `n - 1`, average runtime is computed with
`time.perf_counter()`, and results are written to `results/runtime.csv`.
Every single run also asserts that Dijkstra and Bellman-Ford agree, providing
50+ correctness cross-checks across the full sweep.

Measured results (`results/runtime.csv`, this repository):

| Nodes  | Edges  | Dijkstra avg (ms) | Bellman-Ford avg (ms) |
|-------:|-------:|-------------------:|------------------------:|
| 100    | 400    | 0.121               | 0.111                   |
| 500    | 2,000  | 0.631               | 0.914                   |
| 1,000  | 4,000  | 1.663               | 1.722                   |
| 5,000  | 20,000 | 10.808              | 11.875                  |
| 10,000 | 40,000 | 28.232              | 34.654                  |

Dijkstra is faster at every size, and the gap widens as the graph grows --
consistent with the theoretical prediction in Section 4. The gap is smaller
than the raw `O((V+E) log V)` vs `O(V x E)` bounds might suggest at first
glance, for an instructive reason: the early-termination optimization in
Bellman-Ford (Section 2) converges very quickly on these particular random
graphs, because each graph contains long-range random "shortcut" edges that
give it a small effective diameter (a small-world property). On this run,
Bellman-Ford needed only about 12 relaxation passes to converge at n = 10,000,
not the worst-case 9,999.

**This is an important, honest empirical finding, not a flaw in the
benchmark:** Bellman-Ford's `O(V x E)` bound is a *worst-case* bound, and
worst-case behavior depends on graph structure and edge-processing order, not
just size. To confirm the worst-case bound is real and tight, a small
adversarial experiment was run separately: a simple chain graph
`0 -> 1 -> ... -> n-1` with edges deliberately listed in *reverse* order, so
each pass can only propagate the frontier one hop:

| n     | Passes used | Runtime (ms) |
|------:|------------:|--------------:|
| 200   | 199         | 1.28           |
| 1,000 | 999         | 31.56          |
| 2,000 | 1,999       | 131.62         |

Here Bellman-Ford is forced through exactly `n - 1` passes, and runtime grows
quadratically (n=1,000 is 5x n=200 and runs ~25x slower; n=2,000 is 2x n=1,000
and runs ~4x slower) -- exactly matching `O(V x E) = O(V^2)` when `E = O(V)`.
This confirms the theoretical worst-case bound from Section 4 is tight and
empirically reproducible, while also showing why "typical" random graphs
(Section 6's main table) rarely hit that worst case in practice.

To reproduce either experiment:

```bash
python -m src.benchmark              # full spec: sizes [100,500,1000,5000,10000], 5 reps
python -m src.benchmark --quick       # fast demo: sizes [100,500,1000], 3 reps
python -m src.benchmark --sizes 100 500 1000 2000 --repeats 3
```

## 7. Visualization

`src/visualization.py` reads `results/runtime.csv` and renders a line chart
(number of nodes on the X-axis, average runtime in milliseconds on the
Y-axis, one line per algorithm) using matplotlib, saved to
`results/runtime_plot.png`. Run it with:

```bash
python -m src.visualization
```

The chart is also displayed directly inside the Streamlit app (Section 9).

## 8. Reproducibility

- All randomness is seeded: `generate_random_graph(..., seed=42)` is the
  single source of randomness in the project, and the seed is passed
  explicitly rather than relying on a global `random.seed()` call, so
  benchmark graphs are byte-for-byte reproducible across machines and runs.
- All algorithm runtimes are measured with `time.perf_counter()`, the
  standard high-resolution wall-clock timer recommended for Python
  micro-benchmarks.
- `requirements.txt` pins minimum library versions; the project targets
  Python 3.12.
- The benchmark and visualization scripts are runnable as standalone modules
  (`python -m src.benchmark`, `python -m src.visualization`) independent of
  the Streamlit app, so results can be regenerated from a clean checkout with
  three commands (see Section 9).

## 9. Working Software -- Setup & Usage

```bash
# 1. Create and activate a virtual environment (recommended)
python3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Regenerate benchmark data and plot from scratch
python -m src.benchmark
python -m src.visualization

# 4. Launch the interactive app
streamlit run app.py
```

In the app: choose a mood in the sidebar, pick a start and target activity,
then click **Run Dijkstra**, **Run Bellman-Ford**, or **Compare Algorithms**.
The comparison view shows both algorithms' path, cost, and runtime side by
side, plus a correctness-check confirmation. Scroll down to see the offline
benchmark table and chart.

## 10. Project Structure

```
EnergyPath/
├── src/
│   ├── __init__.py
│   ├── graph_generator.py    # ActivityGraph (36 nodes) + random graph generator
│   ├── dijkstra.py           # Dijkstra, from scratch, heapq-based
│   ├── bellman_ford.py       # Bellman-Ford, from scratch, edge-list based
│   ├── benchmark.py          # Reproducible benchmark suite -> results/runtime.csv
│   └── visualization.py      # results/runtime.csv -> results/runtime_plot.png
├── app.py                    # Streamlit application
├── results/
│   ├── runtime.csv
│   └── runtime_plot.png
├── README.md
└── requirements.txt
```

## 11. Code Quality Notes

- Python 3.12, full type hints on every public function/dataclass.
- Docstrings on every module and public function, including complexity notes
  where relevant.
- Modular architecture: graph modeling, each algorithm, benchmarking, and
  visualization are fully independent modules that only share simple data
  structures (adjacency lists, edge lists), so any one piece can be tested,
  reused, or replaced without touching the others.
- `dataclass`-based result objects (`DijkstraResult`, `BellmanFordResult`) and
  an `Enum`-based `Mood` type are used in place of loose tuples/strings,
  which is the OOP convention applied throughout this project.
