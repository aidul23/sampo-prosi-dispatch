"""Tests for address parsing, address register, geocoding and road-distance stop order."""

import io
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from app import address_book, geocoding_service, plan_storage, stop_optimizer_service
from app.address_parser import parse_address
from app.excel_service import export_driver_sheets, parse_orders_from_excel
from app.models import DriverCapacity, Order
from app.stop_optimizer_service import optimize_stop_order


@pytest.fixture()
def temp_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(plan_storage, "DB_PATH", Path(tmp) / "test.db")
        plan_storage.init_db()
        yield


# --- address parsing -------------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("Valio, Tuupakantie 10, 01740 Vantaa p. 040 123 4567", "Tuupakantie 10, 01740 Vantaa"),
        ("Kesko Hatanpään valtatie 1 B 33100 Tampere", "Hatanpään valtatie 1 B, 33100 Tampere"),
        ("K-Market TUUPAKANTIE 10 01740 VANTAA", "TUUPAKANTIE 10, 01740 Vantaa"),
        ("Stockmann Aleksanterinkatu 52, Helsinki", "Aleksanterinkatu 52, Helsinki"),
        ("33100 Tampere", "33100 Tampere"),
        ("Lidl Laukaa", ""),
        ("Valio Espoo 0401234567", ""),
    ],
)
def test_parse_address(text, expected):
    assert parse_address(text).text == expected


def _excel(rows, header):
    buffer = io.BytesIO()
    pd.DataFrame(rows, columns=header).to_excel(buffer, index=False)
    return buffer.getvalue()


def test_excel_address_column_and_consignee_fallback():
    data = _excel(
        [
            ["Asiakas Oy", "", "Valio Espoo", 4, "", "", "Tekniikantie 2, 02150 Espoo"],
            ["Asiakas Oy", "", "Kauppa, Tuupakantie 10, 01740 Vantaa", 2, "", "", ""],
            ["Asiakas Oy", "", "Lidl Laukaa", 3, "", "", ""],
        ],
        ["Asiakas", "", "Vastaanottaja", "Lavat", "", "Kuski", "Osoite"],
    )
    orders = parse_orders_from_excel(data)
    assert [o.address for o in orders] == [
        "Tekniikantie 2, 02150 Espoo",
        "Tuupakantie 10, 01740 Vantaa",
        "",
    ]
    assert orders[0].routeArea == "Espoo"


def test_postal_city_fills_unknown_route_area():
    data = _excel(
        [["Asiakas Oy", "", "Ravintola X, Kauppakatu 5, 40100 Jyväskylä", 2, "", ""]],
        ["Asiakas", "", "Vastaanottaja", "Lavat", "", "Kuski"],
    )
    order = parse_orders_from_excel(data)[0]
    assert order.routeArea == "Jyväskylä"
    assert order.warning is None


def test_export_has_address_column():
    orders = [Order(id="1", consignee="X", address="Tuupakantie 10, 01740 Vantaa", deliveryDriver="A")]
    workbook = pd.ExcelFile(io.BytesIO(export_driver_sheets(orders, [])))
    sheet = workbook.parse("Full Plan")
    assert "Address" in sheet.columns
    assert sheet["Address"][0] == "Tuupakantie 10, 01740 Vantaa"


# --- address register ------------------------------------------------------

def test_address_book_matches_normalized_consignee(temp_db):
    address_book.upsert_entry("Valio Espoo", "Tekniikantie 2, 02150 Espoo")
    orders = [
        Order(id="1", consignee="VALIO ESPOO 040 123 4567"),
        Order(id="2", consignee="Valio Espoo", address="Other street 1"),
        Order(id="3", consignee="Lidl Laukaa"),
    ]
    assert address_book.apply_address_book(orders) == 1
    assert orders[0].address == "Tekniikantie 2, 02150 Espoo"
    assert orders[1].address == "Other street 1"  # explicit address is kept
    assert orders[2].address == ""


def test_address_book_upsert_replaces(temp_db):
    first = address_book.upsert_entry("Valio Espoo", "Old 1")
    second = address_book.upsert_entry("valio espoo", "New 2")
    assert first.id == second.id
    entries = address_book.list_entries()
    assert len(entries) == 1 and entries[0].address == "New 2"
    assert address_book.delete_entry(first.id)
    assert address_book.list_entries() == []


# --- geocoding -------------------------------------------------------------

def test_geocode_uses_postal_fallback_and_cache(temp_db, monkeypatch):
    monkeypatch.setenv("GEOCODING_ENABLED", "1")
    calls = []

    def fake_search(query):
        calls.append(query)
        if query == "33100 Tampere":
            return (61.49, 23.76)
        if query.startswith("Tuupakantie"):
            return (60.27, 24.94)
        return None

    monkeypatch.setattr(geocoding_service, "_nominatim_search", fake_search)
    orders = [
        Order(id="1", consignee="A", address="Tuupakantie 10, 01740 Vantaa"),
        Order(id="2", consignee="B", address="Unknownkatu 9, 33100 Tampere"),
        Order(id="3", consignee="C"),  # no address -> untouched
    ]
    result = geocoding_service.geocode_orders(orders)
    by_id = {o.id: o for o in result.orders}
    assert by_id["1"].geocodePrecision == "address"
    assert by_id["2"].geocodePrecision == "postal_code"
    assert by_id["2"].lat == 61.49
    assert by_id["3"].lat is None
    assert (result.located, result.pending, result.failed) == (2, 0, 0)

    calls.clear()
    fresh = [Order(id="9", consignee="A", address="Tuupakantie 10, 01740 Vantaa")]
    geocoding_service.geocode_orders(fresh)
    assert calls == []  # served from cache


def test_geocode_batches_and_reports_pending(temp_db, monkeypatch):
    monkeypatch.setenv("GEOCODING_ENABLED", "1")
    monkeypatch.setattr(geocoding_service, "MAX_LOOKUPS_PER_CALL", 2)
    monkeypatch.setattr(geocoding_service, "_nominatim_search", lambda q: (60.0, 25.0))
    orders = [Order(id=str(i), address=f"Testitie {i}, 0010{i} Helsinki") for i in range(5)]
    first = geocoding_service.geocode_orders(orders)
    assert (first.located, first.pending) == (2, 3)
    second = geocoding_service.geocode_orders(first.orders)
    assert (second.located, second.pending) == (4, 1)


def test_geocode_network_error_is_not_cached(temp_db, monkeypatch):
    monkeypatch.setenv("GEOCODING_ENABLED", "1")

    def boom(query):
        raise OSError("offline")

    monkeypatch.setattr(geocoding_service, "_nominatim_search", boom)
    result = geocoding_service.geocode_orders([Order(id="1", address="Testitie 1, 00100 Helsinki")])
    assert result.pending == 1 and result.failed == 0
    assert any("unavailable" in note for note in result.notes)


# --- stop order with coordinates / road distances ---------------------------

DRIVERS = [DriverCapacity(driverName="A", truckCapacity=48)]


def test_stop_order_uses_exact_coordinates():
    # Same route area, but real coordinates: the western stop is nearer the depot.
    far = Order(id="far", consignee="Far", routeArea="Tampere", deliveryDriver="A",
                lat=61.45, lng=23.85, geocodePrecision="address")
    near = Order(id="near", consignee="Near", routeArea="Tampere", deliveryDriver="A",
                 lat=61.52, lng=23.60, geocodePrecision="address")
    result = optimize_stop_order([far, near], DRIVERS)
    seq = {o.id: o.stopSequence for o in result.orders}
    assert seq == {"near": 1, "far": 2}


def test_stop_order_prefers_road_matrix(monkeypatch):
    orders = [
        Order(id="x", consignee="X", routeArea="Vantaa", deliveryDriver="A", lat=60.3, lng=25.0),
        Order(id="y", consignee="Y", routeArea="Seinäjoki", deliveryDriver="A", lat=62.8, lng=22.8),
    ]

    # Pretend roads make Vantaa closer than Seinäjoki from the depot.
    def fake_matrix(points):
        return [[0, 100, 300], [100, 0, 400], [300, 400, 0]]

    monkeypatch.setattr(stop_optimizer_service, "road_distance_matrix", fake_matrix)
    result = optimize_stop_order(orders, DRIVERS)
    seq = {o.id: o.stopSequence for o in result.orders}
    assert seq == {"x": 1, "y": 2}
    assert "road distances" in result.notes[0]
