"""Sample demo orders mimicking a typical daily Excel dispatch sheet."""

import uuid
from typing import List

from .models import Order
from .planning_service import fin_equivalent


def _order(**kwargs) -> Order:
    order = Order(id=str(uuid.uuid4())[:8], **kwargs)
    order.finEquivalent = fin_equivalent(order.pallets, order.palletType, order.stackable)
    return order


def get_sample_orders() -> List[Order]:
    return [
        _order(
            customer="Kespro Oy",
            pickupDriver="Matti",
            consignee="Ravintola Aalto, Tampere",
            pallets=6,
            palletType="FIN",
            stackable=False,
            extraInfo="Cold chain, deliver before 10:00",
            deliveryDriver="Driver A",
            routeArea="Tampere keskusta",
            status="PLANNED",
        ),
        _order(
            customer="Valio Jakelu",
            pickupDriver="Matti",
            consignee="K-Market Hervanta",
            pallets=10,
            palletType="EUR",
            stackable=False,
            extraInfo="",
            deliveryDriver="Driver A",
            routeArea="Hervanta",
            status="PLANNED",
        ),
        _order(
            customer="Sinebrychoff",
            pickupDriver="Jukka",
            consignee="S-Market Lielahti",
            pallets=12,
            palletType="FIN",
            stackable=False,
            extraInfo="Heavy beverage pallets",
            deliveryDriver="Driver B",
            routeArea="Lielahti",
            status="PLANNED",
        ),
        _order(
            customer="Transval",
            pickupDriver="Jukka",
            consignee="Prisma Kaleva",
            pallets=8,
            palletType="EUR",
            stackable=True,
            extraInfo="Stackable boxes",
            deliveryDriver="Driver B",
            routeArea="Kaleva",
            status="NEW",
        ),
        _order(
            customer="Posti Freight",
            pickupDriver="Antti",
            consignee="Tokmanni Nokia",
            pallets=14,
            palletType="FIN",
            stackable=False,
            extraInfo="Tail lift needed",
            deliveryDriver="Driver C",
            routeArea="Nokia",
            status="NEW",
        ),
        _order(
            customer="DSV",
            pickupDriver="Antti",
            consignee="Puuilo Ylöjärvi",
            pallets=20,
            palletType="FIN",
            stackable=False,
            extraInfo="Long goods on top",
            deliveryDriver="Driver C",
            routeArea="Ylöjärvi",
            status="NEW",
        ),
        _order(
            customer="Schenker",
            pickupDriver="Matti",
            consignee="Motonet Pirkkala",
            pallets=15,
            palletType="EUR",
            stackable=False,
            extraInfo="Carry-over from yesterday",
            deliveryDriver="Driver C",
            routeArea="Pirkkala",
            status="CARRY_OVER",
        ),
        _order(
            customer="Kaukokiito",
            pickupDriver="Jukka",
            consignee="Rautia Kangasala",
            pallets=4,
            palletType="OTHER",
            stackable=False,
            extraInfo="Oversized item, check dimensions",
            deliveryDriver="",
            routeArea="Kangasala",
            status="NEW",
        ),
    ]
