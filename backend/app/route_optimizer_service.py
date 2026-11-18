"""Rule-based route assignment: group by route area, respect truck capacity."""

from collections import defaultdict
from typing import List

from .models import (
    DriverCapacity,
    OptimizationChange,
    OptimizeMode,
    OptimizeResponse,
    Order,
)
from .planning_service import calculate_plan, fin_equivalent


def _normalize_area(route_area: str) -> str:
    area = route_area.strip()
    return area if area else "Unspecified"


def _remaining_capacity(
    capacity_by_driver: dict[str, float], used_by_driver: dict[str, float], driver: str
) -> float:
    return capacity_by_driver.get(driver, 0.0) - used_by_driver.get(driver, 0.0)


def _pick_driver_for_cluster(
    drivers: List[DriverCapacity],
    capacity_by_driver: dict[str, float],
    used_by_driver: dict[str, float],
    driver_areas: dict[str, set[str]],
    area: str,
    cluster_load: float,
) -> str | None:
    eligible: list[tuple[str, bool, float]] = []
    for driver in drivers:
        name = driver.driverName
        remaining = _remaining_capacity(capacity_by_driver, used_by_driver, name)
        if remaining >= cluster_load:
            affinity = area in driver_areas.get(name, set())
            eligible.append((name, affinity, remaining))

    if not eligible:
        return None

    eligible.sort(key=lambda item: (item[1], item[2]), reverse=True)
    return eligible[0][0]


def _pick_driver_for_order(
    drivers: List[DriverCapacity],
    capacity_by_driver: dict[str, float],
    used_by_driver: dict[str, float],
    driver_areas: dict[str, set[str]],
    area: str,
    order_load: float,
) -> str | None:
    eligible: list[tuple[str, bool, float]] = []
    for driver in drivers:
        name = driver.driverName
        remaining = _remaining_capacity(capacity_by_driver, used_by_driver, name)
        if remaining >= order_load:
            affinity = area in driver_areas.get(name, set())
            eligible.append((name, affinity, remaining))

    if not eligible:
        return None

    eligible.sort(key=lambda item: (item[1], item[2]), reverse=True)
    return eligible[0][0]


def optimize_routes(
    orders: List[Order],
    drivers: List[DriverCapacity],
    mode: OptimizeMode = "unassigned_only",
) -> OptimizeResponse:
    """Suggest driver assignments grouped by route area within capacity."""
    if not drivers:
        return OptimizeResponse(
            orders=list(orders),
            changes=[],
            routeSummaries=[],
            notes=["No drivers defined — cannot optimize routes."],
        )

    result_orders = [Order(**order.model_dump()) for order in orders]
    capacity_by_driver = {d.driverName: d.truckCapacity for d in drivers}
    used_by_driver: dict[str, float] = {d.driverName: 0.0 for d in drivers}
    driver_areas: dict[str, set[str]] = {d.driverName: set() for d in drivers}
    previous_drivers = {order.id: order.deliveryDriver.strip() for order in result_orders}

    for order in result_orders:
        order.finEquivalent = fin_equivalent(
            order.pallets, order.palletType, order.stackable
        )

    if mode == "all":
        for order in result_orders:
            order.deliveryDriver = ""
        used_by_driver = {name: 0.0 for name in capacity_by_driver}
        driver_areas = {name: set() for name in capacity_by_driver}
        to_optimize = list(result_orders)
    else:
        for order in result_orders:
            driver = order.deliveryDriver.strip()
            if driver:
                used_by_driver[driver] = used_by_driver.get(driver, 0.0) + order.finEquivalent
                driver_areas.setdefault(driver, set()).add(_normalize_area(order.routeArea))
        to_optimize = [order for order in result_orders if not order.deliveryDriver.strip()]

    area_clusters: dict[str, list[Order]] = defaultdict(list)
    for order in to_optimize:
        area_clusters[_normalize_area(order.routeArea)].append(order)

    sorted_clusters = sorted(
        area_clusters.items(),
        key=lambda item: -sum(order.finEquivalent for order in item[1]),
    )

    changes: List[OptimizationChange] = []
    notes: List[str] = []

    for area, cluster_orders in sorted_clusters:
        cluster_load = sum(order.finEquivalent for order in cluster_orders)
        driver = _pick_driver_for_cluster(
            drivers, capacity_by_driver, used_by_driver, driver_areas, area, cluster_load
        )

        if driver:
            for order in cluster_orders:
                prev = previous_drivers[order.id] if mode == "all" else order.deliveryDriver.strip()
                order.deliveryDriver = driver
                used_by_driver[driver] += order.finEquivalent
                driver_areas.setdefault(driver, set()).add(area)
                if prev != driver:
                    changes.append(
                        OptimizationChange(
                            orderId=order.id,
                            consignee=order.consignee,
                            routeArea=area,
                            previousDriver=prev,
                            suggestedDriver=driver,
                            reason=f"Area cluster assigned to {driver} (best remaining capacity)",
                        )
                    )
            notes.append(
                f"Assigned {len(cluster_orders)} {area} order(s) to {driver} "
                f"({cluster_load:.1f} FIN)"
            )
            continue

        sorted_orders = sorted(cluster_orders, key=lambda o: -o.finEquivalent)
        assigned_count = 0
        for order in sorted_orders:
            pick = _pick_driver_for_order(
                drivers,
                capacity_by_driver,
                used_by_driver,
                driver_areas,
                area,
                order.finEquivalent,
            )
            if not pick:
                continue

            prev = previous_drivers[order.id] if mode == "all" else order.deliveryDriver.strip()
            order.deliveryDriver = pick
            used_by_driver[pick] += order.finEquivalent
            driver_areas.setdefault(pick, set()).add(area)
            assigned_count += 1
            if prev != pick:
                changes.append(
                    OptimizationChange(
                        orderId=order.id,
                        consignee=order.consignee,
                        routeArea=area,
                        previousDriver=prev,
                        suggestedDriver=pick,
                        reason=f"Partial cluster split — assigned to {pick} (remaining capacity)",
                    )
                )

        leftover = len(cluster_orders) - assigned_count
        if assigned_count:
            notes.append(
                f"Split {area} cluster: {assigned_count} order(s) assigned, "
                f"{leftover} left unassigned"
            )
        elif leftover:
            notes.append(
                f"{leftover} order(s) in {area} left unassigned — no driver capacity"
            )

    optimized_orders, summaries = calculate_plan(result_orders, drivers)
    return OptimizeResponse(
        orders=optimized_orders,
        changes=changes,
        routeSummaries=summaries,
        notes=notes,
    )
