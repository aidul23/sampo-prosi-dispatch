"""Tests for distance-based driver assignment (capacitated vehicle routing)."""

import pytest

from app import vrp
from app.models import DriverCapacity, Order
from app.route_optimizer_service import optimize_routes

DRIVERS = [
    DriverCapacity(driverName="Driver A", truckCapacity=48),
    DriverCapacity(driverName="Driver B", truckCapacity=44),
    DriverCapacity(driverName="Driver C", truckCapacity=40),
]

# Real-ish coordinates for three clearly separate regions.
PLACES = {
    "Helsinki": (60.17, 24.94),
    "Vantaa": (60.29, 25.04),
    "Espoo": (60.21, 24.66),
    "Oulu": (65.01, 25.47),
    "Kuopio": (62.89, 27.68),
    "Kajaani": (64.23, 27.73),
    "Turku": (60.45, 22.27),
    "Pori": (61.48, 21.80),
    "Rauma": (61.13, 21.51),
}


def _order(oid, place, fin=4.0, driver="", status="NEW", locate=True):
    lat, lng = PLACES.get(place, (None, None))
    return Order(
        id=oid,
        consignee=f"{place} {oid}",
        routeArea=place,
        pallets=fin,
        finEquivalent=fin,
        deliveryDriver=driver,
        status=status,
        lat=lat if locate else None,
        lng=lng if locate else None,
        geocodePrecision="address" if locate and lat else None,
    )


def _regions(result):
    by_driver = {}
    for o in result.orders:
        if o.deliveryDriver:
            by_driver.setdefault(o.deliveryDriver, set()).add(o.routeArea)
    return by_driver


def _region_of(area):
    return {
        "Helsinki": "south", "Vantaa": "south", "Espoo": "south",
        "Oulu": "north", "Kuopio": "north", "Kajaani": "north",
        "Turku": "west", "Pori": "west", "Rauma": "west",
    }[area]


def test_each_truck_gets_one_coherent_region():
    orders = [
        _order(str(i), place, fin=4)
        for i, place in enumerate(["Helsinki", "Oulu", "Turku", "Vantaa", "Kuopio",
                                   "Pori", "Espoo", "Kajaani", "Rauma"])
    ]
    result = optimize_routes(orders, DRIVERS)
    assert all(o.deliveryDriver for o in result.orders)
    regions = {d: {_region_of(a) for a in areas} for d, areas in _regions(result).items()}
    # The far north is never combined with the south/west coast on one truck.
    for driver_regions in regions.values():
        assert not ("north" in driver_regions and len(driver_regions) > 1), regions
    # Orders of the same northern region ride together.
    north_drivers = {o.deliveryDriver for o in result.orders if _region_of(o.routeArea) == "north"}
    assert len(north_drivers) == 1


def test_small_local_plan_uses_one_truck():
    # Two orders in the same city should not be split across trucks.
    orders = [_order("1", "Helsinki"), _order("2", "Vantaa")]
    result = optimize_routes(orders, DRIVERS)
    assert len({o.deliveryDriver for o in result.orders}) == 1


def test_capacity_is_never_exceeded():
    orders = [_order(str(i), place, fin=9) for i, place in
              enumerate(["Helsinki", "Vantaa", "Espoo"] * 5)]  # 135 FIN > 132
    result = optimize_routes(orders, DRIVERS)
    for summary in result.routeSummaries:
        assert summary.usedCapacity <= summary.capacity
    assert any(not o.deliveryDriver for o in result.orders)
    assert any("not enough truck capacity" in n for n in result.notes)


def test_existing_assignments_are_respected_and_extended():
    orders = [
        _order("1", "Oulu", driver="Driver C"),
        _order("2", "Kuopio"),
        _order("3", "Helsinki"),
    ]
    result = optimize_routes(orders, DRIVERS, mode="unassigned_only")
    by_id = {o.id: o.deliveryDriver for o in result.orders}
    assert by_id["1"] == "Driver C"
    assert by_id["2"] and by_id["3"]
    assert by_id["3"] != "Driver C"  # Helsinki never joins the Oulu truck
    assert by_id["2"] != by_id["3"]  # Kuopio and Helsinki are different directions


def test_nearby_order_joins_existing_route():
    orders = [_order("1", "Helsinki", driver="Driver B"), _order("2", "Espoo")]
    result = optimize_routes(orders, DRIVERS, mode="unassigned_only")
    assert {o.id: o.deliveryDriver for o in result.orders}["2"] == "Driver B"


def test_far_regions_are_not_merged_into_one_long_route():
    # Plenty of capacity on one truck, but Helsinki + Oulu would be ~1350 km.
    orders = [_order("1", "Helsinki"), _order("2", "Oulu")]
    result = optimize_routes(orders, DRIVERS)
    assert len({o.deliveryDriver for o in result.orders}) == 2


def test_unused_truck_is_reported():
    result = optimize_routes([_order("1", "Helsinki")], DRIVERS)
    assert sum("no orders" in n for n in result.notes) == 2


def test_unknown_location_and_delivered_are_left_alone():
    orders = [
        _order("1", "Helsinki"),
        _order("2", "Unspecified", locate=False),
        _order("3", "Oulu", status="DELIVERED"),
    ]
    result = optimize_routes(orders, DRIVERS)
    by_id = {o.id: o.deliveryDriver for o in result.orders}
    assert by_id["2"] == "" and by_id["3"] == ""
    assert any("location unknown" in n for n in result.notes)
    assert any("delivered" in n for n in result.notes)


def test_all_mode_reports_orders_that_lose_their_truck():
    orders = [_order(str(i), "Helsinki", fin=30, driver="Driver A") for i in range(5)]
    result = optimize_routes(orders, DRIVERS, mode="all")
    lost = [c for c in result.changes if c.suggestedDriver == ""]
    assert len(lost) == 2  # 150 FIN, only three trucks of >=30
    assert all("capacity" in c.reason for c in lost)


def test_reasons_explain_km_tradeoff():
    orders = [_order("1", "Helsinki"), _order("2", "Oulu"), _order("3", "Turku")]
    result = optimize_routes(orders, DRIVERS)
    assert all("km" in c.reason for c in result.changes)
    assert any("round trip" in n for n in result.notes)


def test_result_is_deterministic():
    orders = [_order(str(i), p) for i, p in enumerate(PLACES)]
    first = optimize_routes(orders, DRIVERS)
    second = optimize_routes(list(reversed(orders)), DRIVERS)
    assert {o.id: o.deliveryDriver for o in first.orders} == {
        o.id: o.deliveryDriver for o in second.orders
    }


def test_uses_road_matrix_when_available(monkeypatch):
    calls = []

    def fake_matrix(points):
        calls.append(len(points))
        return None  # routing unavailable -> approximate distances

    monkeypatch.setattr(vrp, "road_distance_matrix", fake_matrix)
    result = optimize_routes([_order("1", "Helsinki"), _order("2", "Oulu")], DRIVERS)
    assert calls == [3]
    assert any("approximate distances" in n for n in result.notes)


@pytest.mark.parametrize("route", [[1, 2, 3, 4], [4, 3, 2, 1], [2, 4, 1, 3]])
def test_improve_route_finds_optimal_small_tour(route):
    # Points on a line east of the depot: optimal round trip visits them in order.
    def d(i, j):
        return abs(i - j) * 10.0

    best = vrp.improve_route(route, d)
    assert vrp.route_cost(best, d) == 80.0
