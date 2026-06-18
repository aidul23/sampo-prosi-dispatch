"""Business logic: pallet conversion, capacity planning, next-day plan."""

from typing import List

from .models import DriverCapacity, Order, RouteSummary

# FIN pallet (1200x1000) is the base unit. EUR pallet is 1200x800 -> 0.8 FIN.
PALLET_FACTORS = {
    "FIN": 1.0,
    "EUR": 0.8,
    "OTHER": 1.0,
}

STACKABLE_DIVISOR = 2.0


def fin_equivalent(pallets: float, pallet_type: str, stackable: bool) -> float:
    factor = PALLET_FACTORS.get(pallet_type, 1.0)
    load = pallets * factor
    if stackable:
        load /= STACKABLE_DIVISOR
    return round(load, 2)


def calculate_plan(
    orders: List[Order], drivers: List[DriverCapacity]
) -> tuple[List[Order], List[RouteSummary]]:
    """Recalculate FIN equivalents, per-driver usage and overload warnings."""
    capacity_by_driver = {d.driverName: d.truckCapacity for d in drivers}
    used_by_driver: dict[str, float] = {name: 0.0 for name in capacity_by_driver}
    count_by_driver: dict[str, int] = {name: 0 for name in capacity_by_driver}

    for order in orders:
        order.finEquivalent = fin_equivalent(
            order.pallets, order.palletType, order.stackable
        )
        order.warning = None
        driver = order.deliveryDriver.strip()
        if driver:
            used_by_driver[driver] = used_by_driver.get(driver, 0.0) + order.finEquivalent
            count_by_driver[driver] = count_by_driver.get(driver, 0) + 1

    summaries: List[RouteSummary] = []
    for driver, used in used_by_driver.items():
        capacity = capacity_by_driver.get(driver, 0.0)
        used = round(used, 2)
        overloaded = used > capacity
        summaries.append(
            RouteSummary(
                driverName=driver,
                capacity=capacity,
                usedCapacity=used,
                remainingCapacity=round(capacity - used, 2),
                overloaded=overloaded,
                ordersCount=count_by_driver.get(driver, 0),
            )
        )

    overloaded_drivers = {s.driverName for s in summaries if s.overloaded}
    for order in orders:
        driver = order.deliveryDriver.strip()
        if driver and driver in overloaded_drivers:
            order.warning = f"Route '{driver}' exceeds truck capacity"
        elif driver and driver not in capacity_by_driver:
            order.warning = f"Driver '{driver}' has no capacity defined"

    summaries.sort(key=lambda s: s.driverName)
    return orders, summaries
