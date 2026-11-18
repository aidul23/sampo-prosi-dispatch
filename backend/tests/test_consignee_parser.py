"""Tests for consignee → route area parsing."""

from app.consignee_parser import infer_route_area


def test_city_only():
    area, confidence = infer_route_area("Turku")
    assert area == "Turku"
    assert confidence == "exact"


def test_business_and_city():
    area, _ = infer_route_area("Valio Espoo")
    assert area == "Espoo"


def test_lidl_city():
    area, _ = infer_route_area("Lidl  Laukaa")
    assert area == "Laukaa"


def test_hyphenated_route():
    area, confidence = infer_route_area("Vantaa-Helsinki")
    assert area == "Vantaa"
    assert confidence == "inferred"


def test_toimitus_destination():
    area, _ = infer_route_area("Valio Kuopio toimitus Valio Espoo")
    assert area == "Espoo"


def test_strip_phone_and_slash():
    area, _ = infer_route_area("Patu Kolmio Lahti / Ovikoodi: 1234")
    assert area == "Lahti"


def test_inex_sipoo():
    area, _ = infer_route_area("Inex Sipoo")
    assert area == "Sipoo"


def test_unrecognized():
    area, confidence = infer_route_area("Hilding Anders")
    assert area == "Unspecified"
    assert confidence == "failed"
