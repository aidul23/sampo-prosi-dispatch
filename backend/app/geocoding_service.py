"""Turn delivery addresses into map coordinates (geocoding).

Uses the OpenStreetMap Nominatim service by default (free, no API key).
Its usage policy allows at most 1 request per second, so:

* every answer (including "not found") is cached in SQLite, and
* one API call geocodes at most ``MAX_LOOKUPS_PER_CALL`` new addresses and
  reports how many are still pending; the frontend calls again until done.

Lookup order per order:
1. full address           -> precision "address"
2. postal code + city     -> precision "postal_code"
3. nothing found          -> no coordinates; map/stop order use the route area centre

Configuration (environment variables):
    GEOCODING_ENABLED   "0" disables all network lookups (cache still used)
    GEOCODER_URL        Nominatim-compatible search endpoint
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from typing import List, Optional

from . import plan_storage
from .address_book import apply_address_book
from .address_parser import parse_address, postal_code_query
from .consignee_parser import _fold
from .models import GeocodeResponse, Order

DEFAULT_GEOCODER_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "SampoDispatchDemo/0.1 (dispatch planning demo)"
MAX_LOOKUPS_PER_CALL = 12
MIN_SECONDS_BETWEEN_REQUESTS = 1.1
REQUEST_TIMEOUT_SECONDS = 10

_rate_lock = threading.Lock()
_last_request_at = 0.0

# Sentinel: "not in cache" (distinct from a cached "not found").
_MISS = object()


def geocoding_enabled() -> bool:
    return os.environ.get("GEOCODING_ENABLED", "1") != "0"


def _query_key(query: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _fold(query)).strip()


def _cache_get(query: str):
    with plan_storage._connect() as conn:
        row = conn.execute(
            "SELECT lat, lng FROM geocode_cache WHERE query_key = ?", (_query_key(query),)
        ).fetchone()
    if row is None:
        return _MISS
    if row["lat"] is None or row["lng"] is None:
        return None
    return (row["lat"], row["lng"])


def _cache_put(query: str, coords: Optional[tuple[float, float]], label: str = "") -> None:
    with plan_storage._connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO geocode_cache (query_key, query, lat, lng, label, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _query_key(query),
                query,
                coords[0] if coords else None,
                coords[1] if coords else None,
                label,
                plan_storage._utc_now(),
            ),
        )
        conn.commit()


def _nominatim_search(query: str) -> Optional[tuple[float, float]]:
    """Single geocoder request (rate limited). Returns (lat, lng) or None.

    Raises on network errors so a temporary outage is not cached as "not found".
    """
    global _last_request_at
    params = urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "countrycodes": "fi", "limit": 1}
    )
    url = f"{os.environ.get('GEOCODER_URL', DEFAULT_GEOCODER_URL)}?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with _rate_lock:
        wait = MIN_SECONDS_BETWEEN_REQUESTS - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                results = json.loads(response.read().decode("utf-8"))
        finally:
            _last_request_at = time.monotonic()

    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def _lookup(query: str, budget: list[int]) -> object:
    """Cached lookup. Returns coords, None (not found) or _MISS (budget used up)."""
    cached = _cache_get(query)
    if cached is not _MISS:
        return cached
    if budget[0] <= 0 or not geocoding_enabled():
        return _MISS
    budget[0] -= 1
    coords = _nominatim_search(query)
    _cache_put(query, coords)
    return coords


def _address_queries(order: Order) -> list[tuple[str, str]]:
    """Queries to try for an order, most precise first: [(query, precision)]."""
    address = order.address.strip()
    parsed = parse_address(address)
    queries: list[tuple[str, str]] = []

    full = address
    area = order.routeArea.strip()
    if not parsed.postal_code and not parsed.city and area and area != "Unspecified":
        full = f"{address}, {area}"  # street only -> add the route area as city
    if parsed.street or not parsed.postal_code:
        queries.append((full, "address"))

    postal = postal_code_query(address)
    if postal:
        queries.append((postal, "postal_code"))
    return queries


def geocode_orders(orders: List[Order]) -> GeocodeResponse:
    """Fill lat/lng for orders with an address. Safe to call repeatedly."""
    result_orders = [Order(**order.model_dump()) for order in orders]
    notes: List[str] = []

    filled = apply_address_book(result_orders)
    if filled:
        notes.append(f"Filled {filled} address(es) from the address register.")

    budget = [MAX_LOOKUPS_PER_CALL]
    located = pending = failed = 0
    network_error: Optional[str] = None

    for order in result_orders:
        if not order.address.strip():
            continue
        if order.lat is not None and order.lng is not None and order.geocodePrecision:
            located += 1
            continue

        order.lat = order.lng = None
        order.geocodePrecision = None
        outcome = "failed"
        for query, precision in _address_queries(order):
            try:
                coords = _lookup(query, budget)
            except Exception as exc:  # network / service error: retry later
                network_error = str(exc)
                outcome = "pending"
                break
            if coords is _MISS:
                outcome = "pending"
                break
            if coords:
                order.lat, order.lng = coords
                order.geocodePrecision = precision
                outcome = "located"
                break

        if outcome == "located":
            located += 1
        elif outcome == "pending":
            pending += 1
        else:
            failed += 1

    if network_error:
        notes.append(f"Geocoding service unavailable, try again later ({network_error}).")
    elif pending and not geocoding_enabled():
        notes.append("Geocoding is disabled on the server (GEOCODING_ENABLED=0).")
    if failed:
        notes.append(
            f"{failed} address(es) could not be found — check spelling or add a postal code. "
            "These orders use the route area centre."
        )

    return GeocodeResponse(
        orders=result_orders,
        located=located,
        pending=pending,
        failed=failed,
        notes=notes,
    )
