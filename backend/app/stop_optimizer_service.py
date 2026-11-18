"""Nearest-neighbor stop sequencing within each driver route.

Each stop is placed at its geocoded address when available, otherwise at its
route area centre. Distances come from real road distances (OSRM) when the
routing service is reachable, else from approximate area / straight-line
distances.
"""

from collections import defaultdict
from typing import List, Optional

from .area_centroids import DEPOT_COORDS, get_centroid, haversine_km
from .area_distances import DEPOT, area_distance
from .models import (
    DriverCapacity,
    Order,
    StopOptimizationChange,
    StopOptimizeResponse,
)
from .planning_service import calculate_plan
from .routing_service import road_distance_matrix


def _has_coords(order: Order) -> bool:
    return order.lat is not None and order.lng is not None


def _point(order: Order) -> tuple[float, float]:
    if _has_coords(order):
        return (order.lat, order.lng)  # type: ignore[return-value]
    return get_centroid(order.routeArea)


def _approx_distance(a: Optional[Order], b: Order) -> float:
    """Fallback km between two stops (a=None means depot)."""
    a_precise = a is None or _has_coords(a)
    if a_precise and _has_coords(b):
        lat1, lng1 = DEPOT_COORDS if a is None else _point(a)
        lat2, lng2 = _point(b)
        return round(haversine_km(lat1, lng1, lat2, lng2), 1)
    return area_distance(DEPOT if a is None else a.routeArea, b.routeArea)


def _build_distance_fn(driver_orders: List[Order]):
    """Return (distance(i, j), uses_roads). Index 0 = depot, i>0 = driver_orders[i-1]."""
    points = [DEPOT_COORDS] + [_point(order) for order in driver_orders]
    matrix = road_distance_matrix(points)

    def node(i: int) -> Optional[Order]:
        return None if i == 0 else driver_orders[i - 1]

    def distance(i: int, j: int) -> float:
        if matrix is not None and matrix[i][j] is not None:
            return matrix[i][j]  # type: ignore[return-value]
        return _approx_distance(node(i), driver_orders[j - 1])

    return distance, matrix is not None


def optimize_stop_order(
    orders: List[Order],
    drivers: List[DriverCapacity],
) -> StopOptimizeResponse:
    """Assign stopSequence per driver using nearest-neighbor from depot."""
    result_orders = [Order(**order.model_dump()) for order in orders]
    by_driver: dict[str, list[Order]] = defaultdict(list)

    for order in result_orders:
        driver = order.deliveryDriver.strip()
        if driver:
            by_driver[driver].append(order)

    changes: List[StopOptimizationChange] = []
    notes: List[str] = []

    for driver_name in sorted(by_driver):
        driver_orders = by_driver[driver_name]
        if not driver_orders:
            continue

        distance, uses_roads = _build_distance_fn(driver_orders)
        unvisited = list(range(1, len(driver_orders) + 1))
        current = 0  # depot
        sequence = 1
        total_km = 0.0

        while unvisited:
            nxt = min(
                unvisited,
                key=lambda j: (
                    distance(current, j),
                    driver_orders[j - 1].consignee,
                    driver_orders[j - 1].id,
                ),
            )
            leg_km = distance(current, nxt)
            total_km += leg_km
            unvisited.remove(nxt)
            next_order = driver_orders[nxt - 1]
            previous = next_order.stopSequence
            next_order.stopSequence = sequence
            if previous != sequence:
                origin = DEPOT if current == 0 else (
                    driver_orders[current - 1].consignee or "previous stop"
                )
                changes.append(
                    StopOptimizationChange(
                        orderId=next_order.id,
                        consignee=next_order.consignee,
                        deliveryDriver=driver_name,
                        routeArea=next_order.routeArea,
                        previousSequence=previous,
                        suggestedSequence=sequence,
                        reason=f"Nearest stop from {origin} (~{leg_km:.0f} km)",
                    )
                )
            current = nxt
            sequence += 1

        located = sum(1 for order in driver_orders if _has_coords(order))
        basis = "road distances" if uses_roads else "approximate distances"
        notes.append(
            f"{driver_name}: sequenced {len(driver_orders)} stop(s) from {DEPOT} "
            f"using {basis}, ~{total_km:.0f} km one way "
            f"({located}/{len(driver_orders)} at exact address/postal code, "
            "others at area centre)"
        )

    for order in result_orders:
        if not order.deliveryDriver.strip():
            order.stopSequence = None

    optimized_orders, summaries = calculate_plan(result_orders, drivers)
    return StopOptimizeResponse(
        orders=optimized_orders,
        changes=changes,
        routeSummaries=summaries,
        notes=notes,
    )
