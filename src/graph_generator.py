"""
-------------------
Defines the EnergyPath problem domain as a weighted directed graph.

Two graph sources are provided:

1. ``ActivityGraph``  -- the fixed, hand-modeled "daily activity" graph
   (36 real activities, mood-adjustable weights). This is the graph used
   by the Streamlit application and the correctness demonstration.

2. ``generate_random_graph`` -- a synthetic random graph generator used
   purely for benchmarking algorithmic performance at scale (100 to
   10,000 nodes). It has no semantic meaning; it exists to stress-test
   Dijkstra and Bellman-Ford under controlled, reproducible conditions.

All edge weights are strictly positive, matching the real-world
assumption that every activity transition costs (or, after the mood
multiplier, still costs) a non-negative amount of mental energy.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple


Edge = Tuple[int, int, float]          # (u, v, weight)
AdjacencyList = Dict[int, List[Tuple[int, float]]]


class Mood(str, Enum):
    """User mood states. Each mood scales every edge weight by a
    fixed multiplier, modeling how perceived energy cost rises as
    tiredness increases."""

    HAPPY = "Happy"
    NEUTRAL = "Neutral"
    TIRED = "Tired"


MOOD_MULTIPLIERS: Dict[Mood, float] = {
    Mood.HAPPY: 1.0,
    Mood.NEUTRAL: 1.2,
    Mood.TIRED: 1.5,
}


@dataclass
class ActivityGraph:
    """A fixed, weighted, directed graph modeling a day's worth of
    activities and the mental-energy cost of moving from one activity
    to the next.

    Vertices: 36 named daily activities.
    Edges:    directed transitions with a *base* energy cost.
    Weights:  base cost * mood multiplier (see ``Mood``).

    The graph is intentionally NOT a simple chain: several activities
    have multiple outgoing transitions with different costs, so that
    Dijkstra and Bellman-Ford have a genuine optimization problem to
    solve rather than a single forced path.
    """

    activities: List[str] = field(default_factory=list)
    name_to_id: Dict[str, int] = field(default_factory=dict)
    base_edges: List[Edge] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.activities:
            self.activities = list(_ACTIVITIES)
        if not self.name_to_id:
            self.name_to_id = {name: i for i, name in enumerate(self.activities)}
        if not self.base_edges:
            self.base_edges = [
                (self.name_to_id[u], self.name_to_id[v], float(w))
                for u, v, w in _BASE_EDGES
            ]

    @property
    def num_nodes(self) -> int:
        return len(self.activities)

    def activity_name(self, node_id: int) -> str:
        return self.activities[node_id]

    def activity_id(self, name: str) -> int:
        return self.name_to_id[name]

    def weighted_edges(self, mood: Mood) -> List[Edge]:
        """Return the edge list with weights scaled by the mood
        multiplier. Used directly by Bellman-Ford."""
        m = MOOD_MULTIPLIERS[mood]
        return [(u, v, w * m) for u, v, w in self.base_edges]

    def adjacency_list(self, mood: Mood) -> AdjacencyList:
        """Return an adjacency-list view with mood-scaled weights.
        Used directly by Dijkstra."""
        adj: AdjacencyList = {i: [] for i in range(self.num_nodes)}
        for u, v, w in self.weighted_edges(mood):
            adj[u].append((v, w))
        return adj

_ACTIVITIES: List[str] = [
    "Wake Up",                # 0
    "Drink Water",             # 1
    "Stretching",              # 2
    "Meditation",               # 3
    "Breakfast",                # 4
    "Check Notifications",      # 5
    "Read News",                 # 6
    "Commute",                    # 7
    "Attend Lecture",             # 8
    "Lab Session",                 # 9
    "Research Reading",            # 10
    "Coding Practice",              # 11
    "Work on Assignment",            # 12
    "Group Discussion",               # 13
    "Project Development",             # 14
    "Documentation Writing",            # 15
    "Brainstorming",                     # 16
    "Coffee Break",                       # 17
    "Power Nap",                           # 18
    "Listen to Music",                      # 19
    "Gym Workout",                           # 20
    "Running",                                # 21
    "Cycling",                                 # 22
    "Organization Meeting",                     # 23
    "Family Time",                               # 24
    "Dinner",                                     # 25
    "Review Progress",                             # 26
    "Prepare Tomorrow",                             # 27
    "Night Study",                                   # 28
    "Sleep",                                          # 29
    "Lunch",                                           # 30
    "Walk Outside",                                     # 31
    "Social Media Break",                                # 32
    "Plan Day",                                           # 33
    "Journaling",                                          # 34
    "Self Study",                                           # 35
]

_BASE_EDGES: List[Tuple[str, str, float]] = [
    # Morning routine 
    ("Wake Up", "Drink Water", 2),
    ("Wake Up", "Check Notifications", 5),
    ("Wake Up", "Breakfast", 9),
    ("Drink Water", "Stretching", 3),
    ("Drink Water", "Breakfast", 4),
    ("Stretching", "Meditation", 2),
    ("Meditation", "Breakfast", 3),
    ("Check Notifications", "Read News", 4),
    ("Read News", "Breakfast", 6),
    ("Breakfast", "Commute", 5),
    ("Breakfast", "Plan Day", 3),
    ("Plan Day", "Commute", 4),
    ("Commute", "Attend Lecture", 6),
    ("Commute", "Lab Session", 7),
    ("Commute", "Coffee Break", 3),

    # Academic block 
    ("Attend Lecture", "Lab Session", 4),
    ("Attend Lecture", "Research Reading", 8),
    ("Attend Lecture", "Coffee Break", 5),
    ("Attend Lecture", "Self Study", 7),
    ("Attend Lecture", "Lunch", 10),
    ("Self Study", "Coding Practice", 5),
    ("Self Study", "Research Reading", 5),
    ("Self Study", "Night Study", 8),
    ("Lab Session", "Coding Practice", 6),
    ("Lab Session", "Coffee Break", 4),
    ("Lab Session", "Lunch", 6),
    ("Research Reading", "Coding Practice", 5),
    ("Research Reading", "Documentation Writing", 7),
    ("Coding Practice", "Work on Assignment", 5),
    ("Coding Practice", "Power Nap", 8),
    ("Coding Practice", "Documentation Writing", 6),
    ("Coffee Break", "Coding Practice", 3),
    ("Coffee Break", "Work on Assignment", 4),

    # Project / work block 
    ("Work on Assignment", "Group Discussion", 6),
    ("Work on Assignment", "Project Development", 7),
    ("Work on Assignment", "Lunch", 5),
    ("Group Discussion", "Brainstorming", 4),
    ("Group Discussion", "Project Development", 5),
    ("Brainstorming", "Project Development", 3),
    ("Project Development", "Documentation Writing", 6),
    ("Project Development", "Organization Meeting", 8),
    ("Documentation Writing", "Organization Meeting", 5),
    ("Documentation Writing", "Review Progress", 4),
    ("Organization Meeting", "Review Progress", 6),

    # Midday break 
    ("Lunch", "Walk Outside", 3),
    ("Lunch", "Power Nap", 4),
    ("Walk Outside", "Listen to Music", 2),
    ("Power Nap", "Listen to Music", 2),
    ("Power Nap", "Coding Practice", 5),
    ("Power Nap", "Gym Workout", 6),

    # Afternoon recharge / fitness 
    ("Listen to Music", "Gym Workout", 5),
    ("Listen to Music", "Social Media Break", 3),
    ("Gym Workout", "Running", 4),
    ("Gym Workout", "Cycling", 4),
    ("Running", "Family Time", 5),
    ("Cycling", "Family Time", 5),
    ("Social Media Break", "Family Time", 4),
    ("Social Media Break", "Night Study", 6),

    # Evening
    ("Review Progress", "Family Time", 4),
    ("Review Progress", "Dinner", 5),
    ("Family Time", "Dinner", 3),
    ("Dinner", "Prepare Tomorrow", 4),
    ("Dinner", "Journaling", 3),
    ("Prepare Tomorrow", "Night Study", 5),
    ("Prepare Tomorrow", "Sleep", 5),
    ("Journaling", "Night Study", 4),
    ("Journaling", "Sleep", 4),
    ("Night Study", "Sleep", 6),
]

def generate_random_graph(
    num_nodes: int,
    avg_out_degree: int = 4,
    seed: int = 42,
    weight_range: Tuple[int, int] = (1, 20),
) -> Tuple[int, List[Edge]]:
    """Generate a reproducible random directed, positively-weighted
    graph for benchmarking purposes.

    A "backbone" Hamiltonian-like path (0 -> 1 -> 2 -> ... -> n-1) is
    always included first so that node ``num_nodes - 1`` is guaranteed
    reachable from node ``0``; this lets every benchmark run compute a
    genuine source-to-target shortest path instead of failing on an
    unreachable target. Additional random edges are then layered on
    top until the requested average out-degree is reached.

    Args:
        num_nodes: number of vertices in the generated graph.
        avg_out_degree: target average out-degree (controls density
            and therefore |E| ~= num_nodes * avg_out_degree).
        seed: RNG seed. The assignment specifies ``random.seed(42)``
            for reproducibility; this is threaded through explicitly
            rather than relying on global RNG state.
        weight_range: inclusive (min, max) range for edge weights.

    Returns:
        (num_nodes, edges) where edges is a list of (u, v, w) tuples.
    """
    rng = random.Random(seed)
    edges: List[Edge] = []
    edge_set = set()

    # Guaranteed backbone path so source=0, target=n-1 is always reachable.
    for i in range(num_nodes - 1):
        w = rng.randint(*weight_range)
        edges.append((i, i + 1, float(w)))
        edge_set.add((i, i + 1))

    # Extra random edges to reach the target density.
    target_edge_count = num_nodes * avg_out_degree
    attempts = 0
    max_attempts = target_edge_count * 10
    while len(edges) < target_edge_count and attempts < max_attempts:
        attempts += 1
        u = rng.randint(0, num_nodes - 1)
        v = rng.randint(0, num_nodes - 1)
        if u == v or (u, v) in edge_set:
            continue
        w = rng.randint(*weight_range)
        edges.append((u, v, float(w)))
        edge_set.add((u, v))

    return num_nodes, edges


def edges_to_adjacency_list(num_nodes: int, edges: List[Edge]) -> AdjacencyList:
    """Convert an edge list into an adjacency list (helper shared by
    benchmarking code so both algorithms consume the *same* graph
    representation source)."""
    adj: AdjacencyList = {i: [] for i in range(num_nodes)}
    for u, v, w in edges:
        adj[u].append((v, w))
    return adj
