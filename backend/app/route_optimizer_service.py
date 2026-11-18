"""Driver assignment: which truck takes which order.

Capacitated vehicle routing from the Lapväärtti terminal:

1. Each order is placed at its geocoded address, or its route area centre.
2. Trucks without orders get a starting stop in a distinct region
   (farthest-first), so routes cover different directions instead of one
   truck criss-crossing the country.
3. Remaining orders are inserted where they add the fewest kilometres
   (regret insertion: orders with only one good option go first),
   never exceeding a truck's FIN capacity.
4. Local search moves / swaps orders between trucks while that shortens
   total driving distance.

Existing assignments are kept in ``unassigned_only`` mode. DELIVERED orders
are never moved. Orders without any known location are left for the planner.
"""

from collections import Counter
from typing import Dict, List

from .models import (
    DriverCapacity,
    OptimizationChange,
    OptimizeMode,
    OptimizeResponse,
    Order,
)
from .planning_service import calculate_plan, fin_equivalent
from .vrp import (
    DEPOT_STOP,
    DistanceMatrix,
    Vehicle,
    assign_vehicles,
    best_insertion,
    is_locatable,
    route_cost,
    stop_for,
)


def _area_label(order: Order) -> str:
    area = order.routeArea.strip()
    return area if area else "Unspecified"


def _main_areas(orders: List[Order], limit: int = 4) -> str:
    counts = Counter(_area_label(o) for o in orders)
    names = [name for name, _ in counts.most_common(limit)]
    more = len(counts) - len(names)
    return ", ".join(names) + (f" +{more} more" if more > 0 else "")


def optimize_routes(
    orders: List[Order],
    drivers: List[DriverCapacity],
    mode: OptimizeMode = "unassigned_only",
) -> OptimizeResponse:
    """Suggest driver assignments that minimise driving distance within capacity."""
    if not drivers:
        return OptimizeResponse(
            orders=list(orders),
            changes=[],
            routeSummaries=[],
            notes=["No drivers defined — cannot optimize routes."],
        )

    result_orders = [Order(**order.model_dump()) for order in orders]
    for order in result_orders:
        order.finEquivalent = fin_equivalent(order.pallets, order.palletType, order.stackable)

    vehicles = [Vehicle(d.driverName, d.truckCapacity) for d in drivers]
    vehicle_names = {v.name for v in vehicles}
    previous = {o.id: o.deliveryDriver.strip() for o in result_orders}

    # Which orders are fixed on a truck, and which may be (re)assigned.
    fixed_orders: Dict[str, List[Order]] = {v.name: [] for v in vehicles}
    candidates: List[Order] = []
    skipped_delivered = 0
    for order in result_orders:
        driver = order.deliveryDriver.strip()
        keep = order.status == "DELIVERED" or (mode == "unassigned_only" and driver)
        if keep:
            if driver in vehicle_names:
                fixed_orders[driver].append(order)
            elif order.status == "DELIVERED" and not driver:
                skipped_delivered += 1
            continue
        order.deliveryDriver = ""
        candidates.append(order)

    unlocatable = [o for o in candidates if not is_locatable(o)]
    candidates = [o for o in candidates if is_locatable(o)]

    # Deterministic order: heavier first, then by name/id.
    candidates.sort(key=lambda o: (-o.finEquivalent, o.consignee, o.id))
    routed: List[Order] = [o for name in sorted(fixed_orders) for o in fixed_orders[name]]
    routed += candidates
    index_of = {o.id: i + 1 for i, o in enumerate(routed)}  # 0 = depot
    order_at = {i + 1: o for i, o in enumerate(routed)}

    notes: List[str] = []
    changes: List[OptimizationChange] = []

    if candidates:
        matrix = DistanceMatrix([DEPOT_STOP] + [stop_for(o) for o in routed])
        loads = {index_of[o.id]: o.finEquivalent for o in routed}
        result = assign_vehicles(
            matrix,
            vehicles,
            {name: [index_of[o.id] for o in lst] for name, lst in fixed_orders.items()},
            [index_of[o.id] for o in candidates],
            loads,
        )

        for name, route in result.routes.items():
            for node in route:
                order_at[node].deliveryDriver = name

        used = {name: sum(loads[n] for n in route) for name, route in result.routes.items()}
        capacity = {v.name: v.capacity for v in vehicles}

        # Explain each change: km it adds to its truck vs the next-best truck.
        for order in candidates:
            name = order.deliveryDriver
            prev = previous[order.id]
            if name == prev:
                continue
            if not name:
                changes.append(
                    OptimizationChange(
                        orderId=order.id,
                        consignee=order.consignee,
                        routeArea=_area_label(order),
                        previousDriver=prev,
                        suggestedDriver="",
                        reason="Not enough truck capacity — left unassigned",
                    )
                )
                continue
            node = index_of[order.id]
            route = result.routes[name]
            without = [n for n in route if n != node]
            own_km = route_cost(route, matrix) - route_cost(without, matrix)
            alternatives = sorted(
                (best_insertion(result.routes[other], node, matrix)[0], other)
                for other in result.routes
                if other != name and used[other] + loads[node] <= capacity[other] + 1e-9
            )
            if alternatives:
                alt_km, alt_name = alternatives[0]
                reason = (
                    f"Adds ~{own_km:.0f} km to {name}'s route "
                    f"({alt_name} would add ~{alt_km:.0f} km)"
                )
            else:
                reason = f"Adds ~{own_km:.0f} km to {name}'s route (no other truck has room)"
            changes.append(
                OptimizationChange(
                    orderId=order.id,
                    consignee=order.consignee,
                    routeArea=_area_label(order),
                    previousDriver=prev,
                    suggestedDriver=name,
                    reason=reason,
                )
            )

        notes.append(
            f"Assigned by shortest total driving distance from the terminal ({matrix.basis}), "
            "within each truck's FIN capacity."
        )
        for vehicle in vehicles:
            route = result.routes[vehicle.name]
            if not route:
                notes.append(f"{vehicle.name}: no orders")
                continue
            route_orders = [order_at[n] for n in route]
            notes.append(
                f"{vehicle.name}: {len(route)} order(s), {used[vehicle.name]:.1f}/"
                f"{vehicle.capacity:g} FIN, ~{route_cost(route, matrix):.0f} km round trip — "
                f"{_main_areas(route_orders)}"
            )
        if result.unassigned:
            lost = [order_at[n] for n in result.unassigned]
            fin = sum(o.finEquivalent for o in lost)
            notes.append(
                f"{len(lost)} order(s) ({fin:.1f} FIN) left unassigned — not enough truck "
                "capacity. Add a driver or raise a capacity."
            )
        if changes:
            notes.append("Run “Optimize stop order” after applying to sequence the stops.")

    if unlocatable:
        notes.append(
            f"{len(unlocatable)} order(s) left unassigned — location unknown "
            f"({', '.join(o.consignee or o.id for o in unlocatable[:3])}"
            f"{'…' if len(unlocatable) > 3 else ''}). Add an address or route area."
        )
    if skipped_delivered:
        notes.append(f"{skipped_delivered} delivered order(s) skipped.")
    if mode == "all":
        # Orders that lost their driver (unassigned now) also count as changes.
        for order in unlocatable:
            if previous[order.id]:
                changes.append(
                    OptimizationChange(
                        orderId=order.id,
                        consignee=order.consignee,
                        routeArea=_area_label(order),
                        previousDriver=previous[order.id],
                        suggestedDriver="",
                        reason="Location unknown — assign manually",
                    )
                )

    optimized_orders, summaries = calculate_plan(result_orders, drivers)
    return OptimizeResponse(
        orders=optimized_orders,
        changes=changes,
        routeSummaries=summaries,
        notes=notes,
    )
