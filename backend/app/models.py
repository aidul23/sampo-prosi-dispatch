"""Pydantic data models for the dispatch planning demo."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

PalletType = Literal["FIN", "EUR", "OTHER"]
OrderStatus = Literal["NEW", "PLANNED", "DELIVERED", "CARRY_OVER"]


class Order(BaseModel):
    id: str
    customer: str = ""
    pickupDriver: str = ""
    consignee: str = ""
    pallets: float = 0
    palletType: PalletType = "FIN"
    stackable: bool = False
    extraInfo: str = ""
    deliveryDriver: str = ""
    routeArea: str = ""
    status: OrderStatus = "NEW"
    finEquivalent: float = 0
    warning: Optional[str] = None


class DriverCapacity(BaseModel):
    driverName: str
    truckCapacity: float


class RouteSummary(BaseModel):
    driverName: str
    capacity: float
    usedCapacity: float
    remainingCapacity: float
    overloaded: bool
    ordersCount: int


class PlanRequest(BaseModel):
    orders: List[Order]
    drivers: List[DriverCapacity] = Field(default_factory=list)


class PlanResponse(BaseModel):
    orders: List[Order]
    routeSummaries: List[RouteSummary]


class ExportRequest(BaseModel):
    orders: List[Order]
    drivers: List[DriverCapacity] = Field(default_factory=list)
    planDate: Optional[str] = None  # ISO date YYYY-MM-DD
