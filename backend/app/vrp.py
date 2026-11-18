"""Vehicle routing core: distances, tour building and capacitated assignment.

Used by both optimizers:

* ``route_optimizer_service`` — which truck takes which order
  (capacitated vehicle routing: regional seeds -> regret insertion -> local search)
* ``stop_optimizer_service`` — in which order a truck visits its stops
  (nearest neighbour + 2-opt / or-opt)

Nodes are integer indices into a ``DistanceMatrix``; index 0 is always the depot.
Routes are lists of node indices *without* the depot. Every truck starts at the
terminal and (with ``ROUND_TRIP``) returns there, so route cost includes the
drive back.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .area_centroids import AREA_CENTROIDS, DEPOT_COORDS, get_centroid, haversine_km, normalize_area_name
from .area_distances import DEPOT, local_area_distance
from .models import Order
from .routing_service import road_distance_matrix

# Straight-line km -> approximate road km when no routing service is available.
ROAD_FACTOR = 1.25
# Trucks return to the terminal after the last delivery.
ROUND_TRIP = True
# Moves must save at least this many km (avoids flip-flopping on rounding noise).
IMPROVEMENT_EPS_KM = 0.5
# A truck with no orders yet only gets its own region if that region's seed
# stop is at least this far from every other route / seed.
SEED_SEPARATION_KM = 75.0
MAX_LOCAL_SEARCH_PASSES = 100
# Long routes are allowed but discouraged: every km of a route beyond
# LONG_ROUTE_KM counts (1 + LONG_ROUTE_PENALTY) times. This stops the
# optimizer from merging far-apart regions (e.g. Helsinki + Oulu) into one
# very long route just because it is marginally fewer total km.
LONG_ROUTE_KM = float(os.environ.get("LONG_ROUTE_KM", "900"))
LONG_ROUTE_PENALTY = 2.0


def penalized(route_km: float) -> float:
    return route_km + LONG_ROUTE_PENALTY * max(0.0, route_km - LONG_ROUTE_KM)


# --- stops & distances -------------------------------------------------------

@dataclass(frozen=True)
class Stop:
    lat: float
    lng: float
    area: str
    exact: bool  # True = geocoded address/postal code (or the depot)


DEPOT_STOP = Stop(DEPOT_COORDS[0], DEPOT_COORDS[1], DEPOT, True)


def has_coords(order: Order) -> bool:
    return order.lat is not None and order.lng is not None


def is_locatable(order: Order) -> bool:
    """True when we know roughly where the order goes (coords or a known area)."""
    if has_coords(order):
        return True
    name = normalize_area_name(order.routeArea)
    return name != "Unspecified" and name in AREA_CENTROIDS


def stop_for(order: Order) -> Stop:
    if has_coords(order):
        return Stop(order.lat, order.lng, order.routeArea, True)  # type: ignore[arg-type]
    lat, lng = get_centroid(order.routeArea)
    return Stop(lat, lng, order.routeArea, False)


def approx_km(a: Stop, b: Stop) -> float:
    """Approximate road km: hand-tuned local matrix for area pairs, else scaled straight line."""
    if not a.exact and not b.exact:
        local = local_area_distance(a.area, b.area)
        if local is not None:
            return float(local)
    return round(haversine_km(a.lat, a.lng, b.lat, b.lng) * ROAD_FACTOR, 1)


class DistanceMatrix:
    """Road distances (OSRM) between stops, falling back to approximations per cell."""

    def __init__(self, stops: Sequence[Stop], use_roads: bool = True):
        self.stops = list(stops)
        n = len(self.stops)
        road = road_distance_matrix([(s.lat, s.lng) for s in self.stops]) if use_roads else None
        self.uses_roads = road is not None
        self._m = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                value = road[i][j] if road is not None else None
                self._m[i][j] = value if value is not None else approx_km(self.stops[i], self.stops[j])

    def __call__(self, i: int, j: int) -> float:
        return self._m[i][j]

    @property
    def basis(self) -> str:
        return "road distances" if self.uses_roads else "approximate distances"


Dist = Callable[[int, int], float]


# --- single-route (tour) helpers ----------------------------------------------

def route_cost(route: Sequence[int], d: Dist) -> float:
    if not route:
        return 0.0
    cost = d(0, route[0]) + sum(d(a, b) for a, b in zip(route, route[1:]))
    if ROUND_TRIP:
        cost += d(route[-1], 0)
    return cost


def best_insertion(route: Sequence[int], node: int, d: Dist) -> Tuple[float, int]:
    """Cheapest position to insert ``node``: returns (added km, position)."""
    if not route:
        return route_cost([node], d), 0
    best_delta, best_pos = math.inf, 0
    seq = [0, *route]
    for pos in range(len(route) + 1):
        prev = seq[pos]
        if pos < len(route):
            nxt = route[pos]
            delta = d(prev, node) + d(node, nxt) - d(prev, nxt)
        elif ROUND_TRIP:
            delta = d(prev, node) + d(node, 0) - d(prev, 0)
        else:
            delta = d(prev, node)
        if delta < best_delta - 1e-9:
            best_delta, best_pos = delta, pos
    return best_delta, best_pos


def _insert(route: List[int], node: int, d: Dist) -> List[int]:
    _, pos = best_insertion(route, node, d)
    return route[:pos] + [node] + route[pos:]


def improve_route(route: Sequence[int], d: Dist) -> List[int]:
    """Local improvement of one tour: 2-opt (segment reversal) + or-opt (move one stop)."""
    best = list(route)
    best_cost = route_cost(best, d)
    improved = True
    while improved and len(best) > 2:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                cost = route_cost(candidate, d)
                if cost < best_cost - 1e-6:
                    best, best_cost, improved = candidate, cost, True
        for idx in range(len(best)):
            node = best[idx]
            rest = best[:idx] + best[idx + 1 :]
            candidate = _insert(rest, node, d)
            cost = route_cost(candidate, d)
            if cost < best_cost - 1e-6:
                best, best_cost, improved = candidate, cost, True
    return best


def build_route(nodes: Sequence[int], d: Dist) -> List[int]:
    """Nearest-neighbour tour from the depot (in the given tie-break order), then improved."""
    remaining = list(nodes)
    route: List[int] = []
    current = 0
    while remaining:
        nxt = min(remaining, key=lambda n: d(current, n))  # min() keeps first on ties
        remaining.remove(nxt)
        route.append(nxt)
        current = nxt
    return improve_route(route, d)


# --- multi-vehicle assignment -------------------------------------------------

@dataclass
class Vehicle:
    name: str
    capacity: float


@dataclass
class AssignmentResult:
    routes: Dict[str, List[int]]
    unassigned: List[int]  # candidates no truck had capacity for


def _pick_seeds(
    candidates: List[int],
    vehicles: List[Vehicle],
    routes: Dict[str, List[int]],
    loads: Dict[int, float],
    d: Dist,
) -> Dict[str, int]:
    """Farthest-first seeds so empty trucks start in distinct regions.

    Seeds only shape the starting solution; local search may still move all
    orders off a seeded truck if that is clearly better (truck not needed).
    """
    empty = sorted(
        (v for v in vehicles if not routes[v.name]), key=lambda v: (-v.capacity, v.name)
    )
    centres = [n for route in routes.values() for n in route]
    pool = list(candidates)
    seeds: Dict[str, int] = {}

    for vehicle in empty:
        feasible = [n for n in pool if loads[n] <= vehicle.capacity]
        if not feasible:
            continue
        if not centres:
            # First region: the stop farthest from the terminal.
            seed = max(feasible, key=lambda n: (d(0, n), -feasible.index(n)))
        else:
            def separation(n: int) -> float:
                return min(min(d(c, n), d(n, c)) for c in centres)

            seed = max(feasible, key=lambda n: (separation(n), -feasible.index(n)))
            if separation(seed) < SEED_SEPARATION_KM:
                break  # remaining stops are close to existing routes; no new region
        seeds[vehicle.name] = seed
        centres.append(seed)
        pool.remove(seed)
    return seeds


def assign_vehicles(
    d: Dist,
    vehicles: List[Vehicle],
    fixed: Dict[str, List[int]],
    candidates: List[int],
    loads: Dict[int, float],
) -> AssignmentResult:
    """Assign candidate nodes to vehicles, minimising driving distance within capacity.

    ``fixed`` nodes stay on their vehicle (they count toward load and route).
    ``candidates`` must be in a deterministic tie-break order.
    """
    capacity = {v.name: v.capacity for v in vehicles}
    routes: Dict[str, List[int]] = {
        v.name: build_route(fixed.get(v.name, []), d) for v in vehicles
    }
    used = {name: sum(loads[n] for n in route) for name, route in routes.items()}
    movable = set(candidates)
    pending = list(candidates)

    # 1. Regional seeds for empty trucks.
    for name, seed in _pick_seeds(pending, vehicles, routes, loads, d).items():
        routes[name] = [seed]
        used[name] += loads[seed]
        pending.remove(seed)
    raw = {name: route_cost(route, d) for name, route in routes.items()}

    def insertion_cost(name: str, node: int) -> float:
        """Penalized km added by inserting node into a route."""
        added, _ = best_insertion(routes[name], node, d)
        return penalized(raw[name] + added) - penalized(raw[name])

    def set_route(name: str, route: List[int]) -> None:
        routes[name] = route
        raw[name] = route_cost(route, d)

    # 2. Regret insertion: place first the orders that would suffer most
    #    from not getting their best truck.
    unassigned: List[int] = []
    while pending:
        best_choice = None  # (priority tuple, node, vehicle)
        for order_rank, node in enumerate(pending):
            options = sorted(
                (insertion_cost(v.name, node), v.name)
                for v in vehicles
                if used[v.name] + loads[node] <= capacity[v.name] + 1e-9
            )
            if not options:
                continue
            regret = options[1][0] - options[0][0] if len(options) > 1 else math.inf
            priority = (regret, loads[node], -options[0][0], -order_rank)
            if best_choice is None or priority > best_choice[0]:
                best_choice = (priority, node, options[0][1])
        if best_choice is None:
            unassigned.extend(pending)  # nothing fits anywhere any more
            break
        _, node, name = best_choice
        set_route(name, _insert(routes[name], node, d))
        used[name] += loads[node]
        pending.remove(node)

    # 3. Local search between routes: relocate one order / swap two orders.
    names = [v.name for v in vehicles]
    for _ in range(MAX_LOCAL_SEARCH_PASSES):
        improved = False
        for a in names:
            for node in list(routes[a]):
                if node not in movable or node not in routes[a]:
                    continue
                without = [n for n in routes[a] if n != node]
                saving = penalized(raw[a]) - penalized(route_cost(without, d))
                best_move = None
                for b in names:
                    if b == a or used[b] + loads[node] > capacity[b] + 1e-9:
                        continue
                    gain = saving - insertion_cost(b, node)
                    if gain > IMPROVEMENT_EPS_KM and (best_move is None or gain > best_move[0]):
                        best_move = (gain, b)
                if best_move:
                    b = best_move[1]
                    set_route(a, improve_route(without, d))
                    set_route(b, improve_route(_insert(routes[b], node, d), d))
                    used[a] -= loads[node]
                    used[b] += loads[node]
                    improved = True

        for ai, a in enumerate(names):
            for b in names[ai + 1 :]:
                for u in list(routes[a]):
                    for v in list(routes[b]):
                        if u not in movable or v not in movable:
                            continue
                        if u not in routes[a] or v not in routes[b]:
                            continue
                        new_used_a = used[a] - loads[u] + loads[v]
                        new_used_b = used[b] - loads[v] + loads[u]
                        if new_used_a > capacity[a] + 1e-9 or new_used_b > capacity[b] + 1e-9:
                            continue
                        new_a = _insert([n for n in routes[a] if n != u], v, d)
                        new_b = _insert([n for n in routes[b] if n != v], u, d)
                        before = penalized(raw[a]) + penalized(raw[b])
                        after = penalized(route_cost(new_a, d)) + penalized(route_cost(new_b, d))
                        if before - after > IMPROVEMENT_EPS_KM:
                            set_route(a, improve_route(new_a, d))
                            set_route(b, improve_route(new_b, d))
                            used[a], used[b] = new_used_a, new_used_b
                            improved = True
        if not improved:
            break

    return AssignmentResult(routes=routes, unassigned=unassigned)
