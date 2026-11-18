"""Road distance matrix between delivery points.

Uses an OSRM server's ``table`` service (driving distances along real roads).
The public OSRM demo server is used by default — fine for a demo; for
production use a self-hosted OSRM or a commercial routing API.

If the service is disabled or unreachable, callers fall back to
approximate (area / straight-line) distances.

Configuration (environment variables):
    ROUTING_ENABLED   "0" disables road distances
    OSRM_URL          OSRM base URL (default: public demo server)
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Optional

DEFAULT_OSRM_URL = "https://router.project-osrm.org"
REQUEST_TIMEOUT_SECONDS = 15
MAX_POINTS = 100  # public OSRM table limit

Point = tuple[float, float]  # (lat, lng)


def routing_enabled() -> bool:
    return os.environ.get("ROUTING_ENABLED", "1") != "0"


def _osrm_table(points: list[Point]) -> list[list[Optional[float]]]:
    """Request a distance matrix in metres from OSRM. Raises on failure."""
    coords = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in points)
    base = os.environ.get("OSRM_URL", DEFAULT_OSRM_URL).rstrip("/")
    url = f"{base}/table/v1/driving/{coords}?annotations=distance"
    request = urllib.request.Request(
        url, headers={"User-Agent": "SampoDispatchDemo/0.1 (dispatch planning demo)"}
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read().decode("utf-8"))
    if body.get("code") != "Ok":
        raise RuntimeError(body.get("message") or body.get("code") or "OSRM error")
    return body["distances"]


def road_distance_matrix(points: list[Point]) -> Optional[list[list[Optional[float]]]]:
    """Road distances in km between all points, or None if unavailable.

    Individual cells may be None when OSRM cannot route between two points.
    Duplicate points are sent once to keep the request small.
    """
    if not routing_enabled() or len(points) < 2:
        return None

    unique: list[Point] = []
    index_of: dict[Point, int] = {}
    mapping: list[int] = []
    for lat, lng in points:
        key = (round(lat, 5), round(lng, 5))
        if key not in index_of:
            index_of[key] = len(unique)
            unique.append(key)
        mapping.append(index_of[key])

    if len(unique) > MAX_POINTS:
        return None
    if len(unique) == 1:
        return [[0.0 for _ in points] for _ in points]

    try:
        metres = _osrm_table(unique)
    except Exception:
        return None

    return [
        [
            None if metres[mapping[i]][mapping[j]] is None
            else round(metres[mapping[i]][mapping[j]] / 1000.0, 1)
            for j in range(len(points))
        ]
        for i in range(len(points))
    ]
