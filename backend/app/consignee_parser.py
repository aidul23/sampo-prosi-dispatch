"""Parse Finnish consignee (Vastaanottaja) text into a normalized route area."""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

ParseConfidence = Literal["exact", "inferred", "failed"]

# Canonical display name keyed by normalized match token (ascii-folded, lowercase).
_AREA_TOKENS: dict[str, str] = {
    "kristiinankaupunki": "Kristiinankaupunki",
    "lapväärtti": "Lapväärtti",
    "lapvaartti": "Lapväärtti",
    "lappfjärd": "Lapväärtti",
    "lappfjard": "Lapväärtti",
    "kantahämeen tuoretuote": "Hämeenlinna",
    "kanta hämeen tuoretuote": "Hämeenlinna",
    "hämeenlinna": "Hämeenlinna",
    "hameenlinna": "Hämeenlinna",
    "janakkala": "Janakkala",
    "järvenpää": "Järvenpää",
    "jarvenpaa": "Järvenpää",
    "lappeenranta": "Lappeenranta",
    "seinäjoki": "Seinäjoki",
    "seinajoki": "Seinäjoki",
    "orimattila": "Orimattila",
    "nousiainen": "Nousiainen",
    "piispanristi": "Piispanristi",
    "kristiinankaupunki": "Kristiinankaupunki",
    "tuusula": "Tuusula",
    "vantaa": "Vantaa",
    "espoo": "Espoo",
    "koivuhaka": "Vantaa",
    "porvoo": "Porvoo",
    "kouvola": "Kouvola",
    "kotka": "Kotka",
    "mikkeli": "Mikkeli",
    "kuopio": "Kuopio",
    "tampere": "Tampere",
    "turku": "Turku",
    "lahti": "Lahti",
    "pori": "Pori",
    "oulu": "Oulu",
    "kaakkuri": "Oulu",
    "laukaa": "Laukaa",
    "sipoo": "Sipoo",
    "kuusjoki": "Kuusjoki",
    "närpiö": "Närpiö",
    "narpiö": "Närpiö",
    "narpi": "Närpiö",
    "laitila": "Laitila",
    "ylöjärvi": "Ylöjärvi",
    "ylojarvi": "Ylöjärvi",
    "helsinki": "Helsinki",
    "sörnäinen": "Helsinki",
    "sornainen": "Helsinki",
    "vaasa": "Vaasa",
    "kokkola": "Kokkola",
    "pietarsaari": "Pietarsaari",
    "rauma": "Rauma",
    "hyvinkää": "Hyvinkää",
    "hyvinkaa": "Hyvinkää",
    "kerava": "Kerava",
    "riihimäki": "Riihimäki",
    "riihimaki": "Riihimäki",
    "forssa": "Forssa",
    "uusikaupunki": "Uusikaupunki",
    "joensuu": "Joensuu",
    "kajaani": "Kajaani",
    "savonlinna": "Savonlinna",
    "iisalmi": "Iisalmi",
    "varkaus": "Varkaus",
    "hamina": "Hamina",
    "loviisa": "Loviisa",
    "tornio": "Tornio",
    "raahe": "Raahe",
    "kaskinen": "Kaskinen",
    "kauhajoki": "Kauhajoki",
    "lapua": "Lapua",
    "kauhava": "Kauhava",
    "valkeakoski": "Valkeakoski",
    "kurikka": "Kurikka",
    "teuva": "Teuva",
    "jyvaskyla": "Jyväskylä",
    "jyväskylä": "Jyväskylä",
    "rovaniemi": "Rovaniemi",
    "jakobstad": "Pietarsaari",
    "karleby": "Kokkola",
    "kristinestad": "Kristiinankaupunki",
    # Tampere sub-areas (sample demo)
    "hervanta": "Hervanta",
    "lielahti": "Lielahti",
    "kaleva": "Kaleva",
    "nokia": "Nokia",
    "pirkkala": "Pirkkala",
    "kangasala": "Kangasala",
}

_SORTED_TOKENS = sorted(_AREA_TOKENS.keys(), key=len, reverse=True)

_PHONE_RE = re.compile(
    r"(?:\+358|0)\s*\d[\d\s\-]{6,}|(?:040|041|042|044|045|050)\s*[\d\-]{5,}",
    re.IGNORECASE,
)
_NOISE_RE = re.compile(
    r"\b(koodi|ovikoodi|ovet|vast\.otto|vast\.?otto)\b.*$",
    re.IGNORECASE,
)


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _clean_consignee(consignee: str) -> str:
    text = consignee.strip().strip("/").strip()
    text = _PHONE_RE.sub(" ", text)
    text = _NOISE_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" /,-")
    return text


def _destination_after_toimitus(text: str) -> str | None:
    folded = _fold(text)
    marker = "toimitus"
    if marker not in folded:
        return None
    idx = folded.rfind(marker)
    return text[idx + len(marker) :].strip()


def _match_area_in_text(text: str) -> str | None:
    folded = _fold(text)
    last_index = -1
    last_area: str | None = None
    for token in _SORTED_TOKENS:
        index = folded.rfind(token)
        if index > last_index:
            last_index = index
            last_area = _AREA_TOKENS[token]
    return last_area


def _match_area_in_part(part: str) -> str | None:
    return _match_area_in_text(_clean_consignee(part))


def infer_route_area(consignee: str) -> tuple[str, ParseConfidence]:
    """Return normalized route area and confidence from consignee text."""
    if not consignee.strip():
        return "Unspecified", "failed"

    destination = _destination_after_toimitus(consignee)
    if destination:
        area = _match_area_in_part(destination)
        if area:
            return area, "inferred"

    cleaned = _clean_consignee(consignee)

    if "-" in cleaned:
        first_part = cleaned.split("-")[0].strip()
        if first_part:
            area = _match_area_in_part(first_part)
            if area:
                return area, "inferred"

    area = _match_area_in_text(cleaned)
    if area:
        return area, "exact" if _fold(cleaned) == _fold(area) else "inferred"

    return "Unspecified", "failed"


def apply_route_area(order_consignee: str, existing_route_area: str) -> tuple[str, str | None]:
    """Fill route area from consignee when Excel left it empty."""
    if existing_route_area.strip():
        return existing_route_area.strip(), None

    area, confidence = infer_route_area(order_consignee)
    if confidence == "failed":
        return area, "Could not parse route area from consignee"
    return area, None
