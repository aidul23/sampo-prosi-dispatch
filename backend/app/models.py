"""Pydantic data models for the dispatch planning demo."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

PalletType = Literal["FIN", "EUR", "OTHER"]
OrderStatus = Literal["NEW", "PLANNED", "DELIVERED", "CARRY_OVER"]
# How precisely an order was located on the map:
#   address     -> street address found
#   postal_code -> postal code area found (street missing or not found)
#   not_found   -> address was looked up but nothing was found
#   None        -> no address / not looked up yet
# Without coordinates, map and routing fall back to the route area centre.
GeocodePrecision = Literal["address", "postal_code", "not_found"]


class Order(BaseModel):
    id: str
    customer: str = ""
    pickupDriver: str = ""
    consignee: str = ""
    address: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    geocodePrecision: Optional[GeocodePrecision] = None
    pallets: float = 0
    palletType: PalletType = "FIN"
    stackable: bool = False
    extraInfo: str = ""
    deliveryDriver: str = ""
    routeArea: str = ""
    status: OrderStatus = "NEW"
    finEquivalent: float = 0
    warning: Optional[str] = None
    stopSequence: Optional[int] = None


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


OptimizeMode = Literal["unassigned_only", "all"]


class OptimizationChange(BaseModel):
    orderId: str
    consignee: str
    routeArea: str
    previousDriver: str
    suggestedDriver: str
    reason: str


class OptimizeRequest(BaseModel):
    orders: List[Order]
    drivers: List[DriverCapacity] = Field(default_factory=list)
    mode: OptimizeMode = "unassigned_only"


class OptimizeResponse(BaseModel):
    orders: List[Order]
    changes: List[OptimizationChange]
    routeSummaries: List[RouteSummary]
    notes: List[str]


class StopOptimizationChange(BaseModel):
    orderId: str
    consignee: str
    deliveryDriver: str
    routeArea: str
    previousSequence: Optional[int]
    suggestedSequence: int
    reason: str


class StopOptimizeRequest(BaseModel):
    orders: List[Order]
    drivers: List[DriverCapacity] = Field(default_factory=list)


class StopOptimizeResponse(BaseModel):
    orders: List[Order]
    changes: List[StopOptimizationChange]
    routeSummaries: List[RouteSummary]
    notes: List[str]


class SavedPlanSummary(BaseModel):
    id: str
    name: str
    planDate: str
    orderCount: int
    updatedAt: str


class SavedPlan(BaseModel):
    id: str
    name: str
    planDate: str
    orders: List[Order]
    drivers: List[DriverCapacity]
    createdAt: str
    updatedAt: str


class SavePlanRequest(BaseModel):
    name: str
    planDate: str
    orders: List[Order]
    drivers: List[DriverCapacity] = Field(default_factory=list)


class GeocodeResponse(BaseModel):
    orders: List[Order]
    located: int  # orders with address/postal-code coordinates
    pending: int  # addresses not yet looked up (call again to continue)
    failed: int  # addresses the geocoder could not find
    notes: List[str]


class AddressBookEntry(BaseModel):
    id: str
    consignee: str
    address: str
    updatedAt: str


class AddressBookUpsert(BaseModel):
    consignee: str
    address: str


class AddressBookBulkUpsert(BaseModel):
    entries: List[AddressBookUpsert]


class OrdersRequest(BaseModel):
    orders: List[Order]
