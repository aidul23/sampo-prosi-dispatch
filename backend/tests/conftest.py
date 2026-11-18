"""Shared test setup: never call external geocoding/routing services."""

import pytest


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setenv("GEOCODING_ENABLED", "0")
    monkeypatch.setenv("ROUTING_ENABLED", "0")
