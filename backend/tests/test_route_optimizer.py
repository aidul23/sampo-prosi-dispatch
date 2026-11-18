"""Tests for route assignment and stop sequence optimization."""

import copy

import pytest

from app.models import DriverCapacity, Order
from app.route_optimizer_service import optimize_routes
from app.stop_optimizer_service import optimize_stop_order


DRIVERS = [
    DriverCapacity(driverName="Driver A", truckCapacity=48),
    DriverCapacity(driverName="Driver B", truckCapacity=44),
    DriverCapacity(driverName="Driver C", truckCapacity=40),
]


def _order(
    order_id: str,
    *,
    route_area: str = "",
    delivery_driver: str = "",
    pallets: float | None = None,
    fin: float | None = None,
) -> Order:
    load = fin if fin is not None else (pallets if pallets is not None else 4)
    pallet_count = pallets if pallets is not None else load
    order = Order(
        id=order_id,
        customer="Test Oy",
        consignee=f"Stop {order_id}",
        pallets=pallet_count,
        routeArea=route_area,
        deliveryDriver=delivery_driver,
        finEquivalent=load,
    )
    return order


def test_unassigned_orders_grouped_by_area():
    orders = [
        _order("1", route_area="Kangasala", delivery_driver=""),
        _order("2", route_area="Kangasala", delivery_driver=""),
        _order("3", route_area="Nokia", delivery_driver="Driver C", fin=10),
    ]
    result = optimize_routes(orders, DRIVERS, mode="unassigned_only")

    assigned = {o.id: o.deliveryDriver for o in result.orders if o.id in {"1", "2"}}
    assert all(driver for driver in assigned.values())
    assert len(set(assigned.values())) == 1
    assert result.orders[2].deliveryDriver == "Driver C"
    assert len(result.changes) == 2


def test_unassigned_only_leaves_existing_assignments():
    orders = [
        _order("1", route_area="Hervanta", delivery_driver="Driver A", fin=10),
        _order("2", route_area="Kangasala", delivery_driver=""),
    ]
    result = optimize_routes(orders, DRIVERS, mode="unassigned_only")

    assert result.orders[0].deliveryDriver == "Driver A"
    assert result.orders[1].deliveryDriver != ""
    assert all(change.orderId == "2" for change in result.changes)


def test_all_mode_can_reassign_every_order():
    orders = [
        _order("1", route_area="Hervanta", delivery_driver="Driver C", fin=8),
        _order("2", route_area="Hervanta", delivery_driver="Driver A", fin=8),
        _order("3", route_area="Nokia", delivery_driver="Driver B", fin=8),
    ]
    result = optimize_routes(copy.deepcopy(orders), DRIVERS, mode="all")

    assert all(order.deliveryDriver for order in result.orders)
    assert len(result.changes) >= 1


def test_over_capacity_cluster_leaves_overflow_unassigned():
    orders = [
        _order("1", route_area="Heavy", delivery_driver="", fin=50),
        _order("2", route_area="Heavy", delivery_driver="", fin=50),
    ]
    result = optimize_routes(orders, DRIVERS, mode="unassigned_only")

    unassigned = [o for o in result.orders if not o.deliveryDriver.strip()]
    assert len(unassigned) >= 1
    assert any("left unassigned" in note for note in result.notes)


def test_stop_order_assigns_sequences_per_driver():
    orders = [
        _order("1", route_area="Nokia", delivery_driver="Driver C", fin=10),
        _order("2", route_area="Hervanta", delivery_driver="Driver C", fin=8),
        _order("3", route_area="Kangasala", delivery_driver="Driver C", fin=4),
    ]
    result = optimize_stop_order(orders, DRIVERS)
    driver_c = [o for o in result.orders if o.deliveryDriver == "Driver C"]
    by_id = {o.id: o.stopSequence for o in driver_c}

    # From Lapväärtti: Nokia first; from Nokia, Kangasala is closer than Hervanta.
    assert sorted(by_id.values()) == [1, 2, 3]
    assert by_id["1"] == 1
    assert by_id["3"] == 2
    assert by_id["2"] == 3
    assert len(result.changes) >= 1
