"""Approximate distances (km) between route areas for stop ordering.

Uses a small hand-tuned matrix for local Tampere-area pairs, then falls back
to haversine distance between area centroids (works nationwide from Lapväärtti).
"""

from .area_centroids import DEPOT, get_centroid, haversine_km

# Symmetric approximate road distances in km for dense Tampere-region pairs.
_AREA_DISTANCES: dict[tuple[str, str], float] = {
    ("tampere", "tampere keskusta"): 0,
    ("tampere", "hervanta"): 8,
    ("tampere", "lielahti"): 7,
    ("tampere", "kaleva"): 4,
    ("tampere", "nokia"): 16,
    ("tampere", "ylöjärvi"): 14,
    ("tampere", "ylojarvi"): 14,
    ("tampere", "pirkkala"): 12,
    ("tampere", "kangasala"): 20,
    ("tampere", "unspecified"): 10,
    ("tampere keskusta", "hervanta"): 8,
    ("tampere keskusta", "lielahti"): 7,
    ("tampere keskusta", "kaleva"): 4,
    ("tampere keskusta", "nokia"): 16,
    ("tampere keskusta", "ylöjärvi"): 14,
    ("tampere keskusta", "ylojarvi"): 14,
    ("tampere keskusta", "pirkkala"): 12,
    ("tampere keskusta", "kangasala"): 20,
    ("tampere keskusta", "unspecified"): 10,
    ("hervanta", "lielahti"): 12,
    ("hervanta", "kaleva"): 9,
    ("hervanta", "nokia"): 18,
    ("hervanta", "ylöjärvi"): 16,
    ("hervanta", "ylojarvi"): 16,
    ("hervanta", "pirkkala"): 14,
    ("hervanta", "kangasala"): 14,
    ("hervanta", "unspecified"): 12,
    ("lielahti", "kaleva"): 6,
    ("lielahti", "nokia"): 12,
    ("lielahti", "ylöjärvi"): 10,
    ("lielahti", "ylojarvi"): 10,
    ("lielahti", "pirkkala"): 8,
    ("lielahti", "kangasala"): 18,
    ("lielahti", "unspecified"): 10,
    ("kaleva", "nokia"): 18,
    ("kaleva", "ylöjärvi"): 16,
    ("kaleva", "ylojarvi"): 16,
    ("kaleva", "pirkkala"): 14,
    ("kaleva", "kangasala"): 22,
    ("kaleva", "unspecified"): 10,
    ("nokia", "ylöjärvi"): 8,
    ("nokia", "ylojarvi"): 8,
    ("nokia", "pirkkala"): 10,
    ("nokia", "kangasala"): 12,
    ("nokia", "unspecified"): 14,
    ("ylöjärvi", "ylojarvi"): 0,
    ("ylöjärvi", "pirkkala"): 6,
    ("ylöjärvi", "kangasala"): 16,
    ("ylojarvi", "pirkkala"): 6,
    ("ylojarvi", "kangasala"): 16,
    ("pirkkala", "kangasala"): 18,
    ("pirkkala", "unspecified"): 12,
    ("kangasala", "unspecified"): 16,
    ("unspecified", "unspecified"): 0,
    ("lapväärtti", "lappfjärd"): 0,
    ("lapväärtti", "kristiinankaupunki"): 5,
    ("lappfjärd", "kristiinankaupunki"): 5,
}


def _symmetric_lookup() -> dict[tuple[str, str], float]:
    lookup: dict[tuple[str, str], float] = {}
    for (area_a, area_b), distance in _AREA_DISTANCES.items():
        lookup[tuple(sorted((area_a, area_b)))] = distance
    return lookup


_DISTANCE_LOOKUP = _symmetric_lookup()


def normalize_area_key(route_area: str) -> str:
    area = route_area.strip().lower()
    if not area:
        return "unspecified"
    if area.startswith("tampere"):
        return "tampere keskusta"
    if area in {"lappfjärd", "lappfjard"}:
        return "lapväärtti"
    return area


def area_distance(from_area: str, to_area: str) -> float:
    """Return approximate km between two route areas."""
    a = normalize_area_key(from_area)
    b = normalize_area_key(to_area)
    if a == b:
        return 0.0
    key = tuple(sorted((a, b)))
    if key in _DISTANCE_LOOKUP:
        return _DISTANCE_LOOKUP[key]

    lat1, lon1 = get_centroid(from_area or DEPOT)
    lat2, lon2 = get_centroid(to_area)
    return round(haversine_km(lat1, lon1, lat2, lon2), 1)
