"""Stop sequencing within each driver route.

Each stop is placed at its geocoded address when available, otherwise at its
route area centre. The tour starts at the Lapväärtti terminal and returns
there; it is built nearest-neighbour first and then improved with 2-opt and
or-opt moves. Distances are real road distances (OSRM) when the routing
service is reachable, else approximate distances.
"""

from collections import defaultdict
from typing import List

from .area_distances import DEPOT
from .models import (
    DriverCapacity,
    Order,
    StopOptimizationChange,
    StopOptimizeResponse,
)
from .planning_service import calculate_plan
from .vrp import DEPOT_STOP, DistanceMatrix, build_route, has_coords, route_cost, stop_for


def optimize_stop_order(
    orders: List[Order],
    drivers: List[DriverCapacity],
) -> StopOptimizeResponse:
    """Assign stopSequence per driver: shortest round trip from the terminal."""
    result_orders = [Order(**order.model_dump()) for order in orders]
    by_driver: dict[str, list[Order]] = defaultdict(list)

    for order in result_orders:
        driver = order.deliveryDriver.strip()
        if driver:
            by_driver[driver].append(order)

    changes: List[StopOptimizationChange] = []
    notes: List[str] = []

    for driver_name in sorted(by_driver):
        # Tie-break order for equal distances: consignee, then id.
        driver_orders = sorted(by_driver[driver_name], key=lambda o: (o.consignee, o.id))
        matrix = DistanceMatrix([DEPOT_STOP] + [stop_for(o) for o in driver_orders])
        route = build_route(list(range(1, len(driver_orders) + 1)), matrix)

        previous_node = 0
        for sequence, node in enumerate(route, start=1):
            order = driver_orders[node - 1]
            leg_km = matrix(previous_node, node)
            previous_seq = order.stopSequence
            order.stopSequence = sequence
            if previous_seq != sequence:
                origin = DEPOT if previous_node == 0 else (
                    driver_orders[previous_node - 1].consignee or "previous stop"
                )
                changes.append(
                    StopOptimizationChange(
                        orderId=order.id,
                        consignee=order.consignee,
                        deliveryDriver=driver_name,
                        routeArea=order.routeArea,
                        previousSequence=previous_seq,
                        suggestedSequence=sequence,
                        reason=f"Next after {origin} (~{leg_km:.0f} km)",
                    )
                )
            previous_node = node

        located = sum(1 for order in driver_orders if has_coords(order))
        notes.append(
            f"{driver_name}: {len(driver_orders)} stop(s) from {DEPOT} using {matrix.basis}, "
            f"~{route_cost(route, matrix):.0f} km round trip "
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
