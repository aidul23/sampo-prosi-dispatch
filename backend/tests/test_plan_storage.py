"""Tests for saved plan persistence."""

import tempfile
from pathlib import Path

import pytest

from app.models import DriverCapacity, Order
from app import plan_storage


@pytest.fixture()
def temp_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_plans.db"
        monkeypatch.setattr(plan_storage, "DB_PATH", db_path)
        plan_storage.init_db()
        yield db_path


def _sample_order(order_id: str = "o1") -> Order:
    return Order(id=order_id, consignee="Test Stop", routeArea="Tampere", pallets=4)


def test_create_and_get_plan(temp_db):
    drivers = [DriverCapacity(driverName="Driver A", truckCapacity=48)]
    created = plan_storage.create_plan(
        "Monday plan", "2026-06-18", [_sample_order()], drivers
    )
    loaded = plan_storage.get_plan(created.id)
    assert loaded is not None
    assert loaded.name == "Monday plan"
    assert loaded.planDate == "2026-06-18"
    assert len(loaded.orders) == 1
    assert loaded.drivers[0].driverName == "Driver A"


def test_list_and_update_plan(temp_db):
    created = plan_storage.create_plan("Draft", "2026-06-18", [], [])
    updated = plan_storage.update_plan(
        created.id,
        "Updated draft",
        "2026-06-19",
        [_sample_order("o2")],
        [DriverCapacity(driverName="Driver B", truckCapacity=40)],
    )
    assert updated is not None
    assert updated.name == "Updated draft"
    assert updated.planDate == "2026-06-19"
    summaries = plan_storage.list_plans()
    assert len(summaries) == 1
    assert summaries[0].orderCount == 1


def test_delete_plan(temp_db):
    created = plan_storage.create_plan("Temp", "2026-06-18", [], [])
    assert plan_storage.delete_plan(created.id) is True
    assert plan_storage.get_plan(created.id) is None
    assert plan_storage.delete_plan(created.id) is False
