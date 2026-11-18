"""Extract a street address / postal code from free-text cells.

The customer's consignee cell (Vastaanottaja) mixes names, phone numbers,
door codes and — optionally — an address, e.g.

    "Valio, Tuupakantie 10, 01740 Vantaa p. 040 123 4567"

This module pulls out the address part so it can be geocoded. It is
deliberately conservative: if nothing that looks like a Finnish street
address or postal code is found, it returns an empty result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .consignee_parser import _PHONE_RE

# Common Finnish / Swedish street-name endings.
_SUFFIXES = (
    "tie|katu|kuja|polku|väylä|vayla|tori|raitti|ranta|kaari|rinne|aukio|"
    "puistikko|bulevardi|valtatie|gatan|vägen|vagen|gränd|grand|stigen|torget"
)
# Either "Hatanpään valtatie 1" (capitalised word + lowercase street word) or
# "Tuupakantie 10" / "TUUPAKANTIE 10" (single word). House number may be
# followed by a letter and/or staircase/apartment ("12 B 3", "4a", "5-7").
_STREET_RE = re.compile(
    r"(?:[A-ZÅÄÖ][a-zåäö\-]+\s+[a-zåäö][a-zåäö\-]*(?:" + _SUFFIXES + r")"
    r"|(?i:[a-zåäö][a-zåäö\-]*(?:" + _SUFFIXES + r")))"
    r"\s+\d{1,4}(?:\s?[a-zA-Z]\b)?(?:\s?[-–]\s?\d{1,4})?"
)
_CITY_AFTER_STREET_RE = re.compile(r"^[,\s]+([A-ZÅÄÖ][a-zåäö\-]{2,})\b")
_POSTAL_RE = re.compile(r"(?<!\d)(\d{5})(?!\d)(?:\s+([A-ZÅÄÖa-zåäö][A-Za-zÅÄÖåäö\-]+))?")


@dataclass
class ParsedAddress:
    street: str = ""
    postal_code: str = ""
    city: str = ""

    @property
    def text(self) -> str:
        """Normalized address string suitable for geocoding / display."""
        place = " ".join(p for p in (self.postal_code, self.city) if p)
        return ", ".join(p for p in (self.street, place) if p)

    @property
    def found(self) -> bool:
        return bool(self.street or self.postal_code)


def parse_address(text: str) -> ParsedAddress:
    """Find street + postal code + city in free text (best effort)."""
    if not text or not text.strip():
        return ParsedAddress()
    cleaned = _PHONE_RE.sub(" ", text)

    result = ParsedAddress()
    street = _STREET_RE.search(cleaned)
    if street:
        result.street = re.sub(r"\s+", " ", street.group(0)).strip()

    postal = _POSTAL_RE.search(cleaned)
    if postal:
        result.postal_code = postal.group(1)
        city = postal.group(2) or ""
        result.city = city.capitalize() if city.isupper() else city
    elif street:
        # "Aleksanterinkatu 52, Helsinki" -> city directly after the street.
        after = _CITY_AFTER_STREET_RE.match(cleaned[street.end():])
        if after:
            result.city = after.group(1)
    return result


def postal_code_query(address: str) -> str:
    """Reduce an address to its 'postal code + city' part (coarser fallback)."""
    parsed = parse_address(address)
    if not parsed.postal_code:
        return ""
    return " ".join(p for p in (parsed.postal_code, parsed.city) if p)
