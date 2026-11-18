"""Approximate WGS84 centroids for Finnish route areas (map pins)."""

from __future__ import annotations

import math

from .consignee_parser import infer_route_area

# lat, lng — approximate municipality / delivery zone centers
AREA_CENTROIDS: dict[str, tuple[float, float]] = {
    "Helsinki": (60.1699, 24.9384),
    "Vantaa": (60.2934, 25.0378),
    "Espoo": (60.2055, 24.6559),
    "Turku": (60.4518, 22.2666),
    "Tampere": (61.4978, 23.7610),
    "Oulu": (65.0121, 25.4651),
    "Lahti": (60.9827, 25.6612),
    "Kuopio": (62.8924, 27.6770),
    "Jyväskylä": (62.2426, 25.7473),
    "Pori": (61.4851, 21.7974),
    "Porvoo": (60.3932, 25.6653),
    "Kotka": (60.4664, 26.9458),
    "Kouvola": (60.8679, 26.7041),
    "Hämeenlinna": (60.9960, 24.4643),
    "Seinäjoki": (62.7909, 22.8404),
    "Rovaniemi": (66.5039, 25.7294),
    "Mikkeli": (61.6886, 27.2723),
    "Lappeenranta": (61.0587, 28.1888),
    "Järvenpää": (60.4736, 25.0899),
    "Tuusula": (60.4038, 25.0260),
    "Sipoo": (60.3754, 25.2691),
    "Janakkala": (60.8975, 24.5970),
    "Laukaa": (62.4141, 25.9515),
    "Orimattila": (60.8048, 25.7294),
    "Nousiainen": (60.6045, 22.5225),
    "Laitila": (60.8759, 21.6977),
    "Kuusjoki": (60.5194, 23.5517),
    "Närpiö": (62.4723, 21.3360),
    "Ylöjärvi": (61.5563, 23.5966),
    "Kristiinankaupunki": (62.2419, 21.5014),
    "Vaasa": (63.0951, 21.6165),
    "Kokkola": (63.8385, 23.1307),
    "Pietarsaari": (63.675, 22.7036),
    "Rauma": (61.1287, 21.5111),
    "Salo": (60.3831, 23.1286),
    "Hyvinkää": (60.6311, 24.8617),
    "Kerava": (60.4034, 25.105),
    "Riihimäki": (60.7377, 24.772),
    "Forssa": (60.8148, 23.6214),
    "Uusikaupunki": (60.8008, 21.408),
    "Joensuu": (62.601, 29.7636),
    "Kajaani": (64.2273, 27.7285),
    "Savonlinna": (61.8686, 28.8796),
    "Iisalmi": (63.56, 27.1907),
    "Varkaus": (62.3159, 27.8731),
    "Imatra": (61.1719, 28.7524),
    "Hamina": (60.5697, 27.1979),
    "Loviisa": (60.4566, 26.225),
    "Kemi": (65.7364, 24.5637),
    "Tornio": (65.8481, 24.1466),
    "Raahe": (64.6847, 24.4789),
    "Kaskinen": (62.3844, 21.2232),
    "Kauhajoki": (62.4317, 22.1794),
    "Lapua": (62.9708, 23.0083),
    "Kauhava": (63.1014, 23.0636),
    "Valkeakoski": (61.2642, 24.031),
    "Kurikka": (62.6167, 22.4),
    "Teuva": (62.4864, 21.7469),
    # Customer terminal: Porintie 382, Lapväärtti (Lappfjärd)
    "Lapväärtti": (62.2408, 21.4472),
    "Lappfjärd": (62.2408, 21.4472),
    "Piispanristi": (60.4200, 22.7000),
    "Unspecified": (61.9241, 25.7482),
    # Tampere sub-areas (sample demo)
    "Tampere keskusta": (61.4978, 23.7610),
    "Hervanta": (61.4470, 23.8580),
    "Lielahti": (61.5120, 23.6700),
    "Kaleva": (61.5050, 23.7900),
    "Nokia": (61.4770, 23.5040),
    "Pirkkala": (61.4650, 23.6330),
    "Kangasala": (61.4640, 24.0660),
}

DEPOT = "Lapväärtti"
DEPOT_ADDRESS = "Porintie 382, Lapväärtti"
DEPOT_COORDS = AREA_CENTROIDS[DEPOT]


def normalize_area_name(route_area: str) -> str:
    area = route_area.strip()
    if not area:
        return "Unspecified"
    if area in AREA_CENTROIDS:
        return area
    inferred, _ = infer_route_area(area)
    return inferred if inferred in AREA_CENTROIDS else area


def get_centroid(route_area: str) -> tuple[float, float]:
    name = normalize_area_name(route_area)
    return AREA_CENTROIDS.get(name, AREA_CENTROIDS["Unspecified"])


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance in km between two WGS84 points."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def all_centroids() -> dict[str, dict[str, float]]:
    return {
        name: {"lat": coords[0], "lng": coords[1]}
        for name, coords in AREA_CENTROIDS.items()
    }
