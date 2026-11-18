"""FastAPI application for the Sampo dispatch planning demo."""

from datetime import date
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .address_book import (
    apply_address_book,
    delete_entry,
    list_entries,
    update_entry,
    upsert_entry,
)
from .area_centroids import DEPOT, DEPOT_ADDRESS, DEPOT_COORDS, all_centroids
from .excel_service import export_driver_sheets, parse_orders_from_excel
from .geocoding_service import geocode_orders
from .models import (
    AddressBookBulkUpsert,
    AddressBookEntry,
    AddressBookUpsert,
    GeocodeResponse,
    OrdersRequest,
    ExportRequest,
    OptimizeRequest,
    OptimizeResponse,
    Order,
    PlanRequest,
    PlanResponse,
    SavePlanRequest,
    SavedPlan,
    SavedPlanSummary,
    StopOptimizeRequest,
    StopOptimizeResponse,
)
from .plan_storage import create_plan, delete_plan, get_plan, init_db, list_plans, update_plan
from .planning_service import calculate_plan
from .route_optimizer_service import optimize_routes
from .sample_data import get_sample_orders
from .stop_optimizer_service import optimize_stop_order

app = FastAPI(title="Sampo Dispatch Planning Demo", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/area-centroids")
def area_centroids() -> dict:
    return {
        "depot": {
            "name": DEPOT,
            "address": DEPOT_ADDRESS,
            "lat": DEPOT_COORDS[0],
            "lng": DEPOT_COORDS[1],
        },
        "areas": all_centroids(),
    }


@app.post("/api/upload-excel", response_model=List[Order])
async def upload_excel(file: UploadFile = File(...)) -> List[Order]:
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls", ".xlsm")):
        raise HTTPException(status_code=400, detail="Please upload an Excel file (.xlsx/.xls)")
    contents = await file.read()
    try:
        orders = parse_orders_from_excel(contents)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse Excel file: {exc}")
    if not orders:
        raise HTTPException(status_code=400, detail="No order rows found in the Excel file")
    apply_address_book(orders)
    return orders


@app.get("/api/sample-orders", response_model=List[Order])
def sample_orders() -> List[Order]:
    orders = get_sample_orders()
    apply_address_book(orders)
    return orders


@app.post("/api/calculate-plan", response_model=PlanResponse)
def calculate(request: PlanRequest) -> PlanResponse:
    orders, summaries = calculate_plan(request.orders, request.drivers)
    return PlanResponse(orders=orders, routeSummaries=summaries)


@app.post("/api/optimize-routes", response_model=OptimizeResponse)
def optimize(request: OptimizeRequest) -> OptimizeResponse:
    if not request.orders:
        raise HTTPException(status_code=400, detail="No orders to optimize")
    return optimize_routes(request.orders, request.drivers, request.mode)


@app.post("/api/optimize-stop-order", response_model=StopOptimizeResponse)
def optimize_stops(request: StopOptimizeRequest) -> StopOptimizeResponse:
    if not request.orders:
        raise HTTPException(status_code=400, detail="No orders to sequence")
    return optimize_stop_order(request.orders, request.drivers)


@app.post("/api/geocode-orders", response_model=GeocodeResponse)
def geocode(request: OrdersRequest) -> GeocodeResponse:
    """Locate order addresses on the map. Call repeatedly while `pending` > 0."""
    return geocode_orders(request.orders)


@app.get("/api/address-book", response_model=List[AddressBookEntry])
def address_book_list() -> List[AddressBookEntry]:
    return list_entries()


@app.post("/api/address-book", response_model=AddressBookEntry)
def address_book_upsert(request: AddressBookUpsert) -> AddressBookEntry:
    try:
        return upsert_entry(request.consignee, request.address)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/address-book/bulk", response_model=List[AddressBookEntry])
def address_book_bulk(request: AddressBookBulkUpsert) -> List[AddressBookEntry]:
    saved = []
    for entry in request.entries:
        if entry.consignee.strip() and entry.address.strip():
            saved.append(upsert_entry(entry.consignee, entry.address))
    return saved


@app.put("/api/address-book/{entry_id}", response_model=AddressBookEntry)
def address_book_update(entry_id: str, request: AddressBookUpsert) -> AddressBookEntry:
    try:
        entry = update_entry(entry_id, request.consignee, request.address)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if entry is None:
        raise HTTPException(status_code=404, detail="Address entry not found")
    return entry


@app.delete("/api/address-book/{entry_id}")
def address_book_delete(entry_id: str) -> dict:
    if not delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Address entry not found")
    return {"status": "deleted", "id": entry_id}


@app.post("/api/address-book/apply", response_model=List[Order])
def address_book_apply(request: OrdersRequest) -> List[Order]:
    """Fill empty addresses in the given orders from the register."""
    orders = [Order(**order.model_dump()) for order in request.orders]
    apply_address_book(orders)
    return orders


@app.get("/api/plans", response_model=List[SavedPlanSummary])
def plans_list() -> List[SavedPlanSummary]:
    return list_plans()


@app.get("/api/plans/{plan_id}", response_model=SavedPlan)
def plans_get(plan_id: str) -> SavedPlan:
    plan = get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@app.post("/api/plans", response_model=SavedPlan)
def plans_create(request: SavePlanRequest) -> SavedPlan:
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Plan name is required")
    return create_plan(request.name, request.planDate, request.orders, request.drivers)


@app.put("/api/plans/{plan_id}", response_model=SavedPlan)
def plans_update(plan_id: str, request: SavePlanRequest) -> SavedPlan:
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Plan name is required")
    plan = update_plan(plan_id, request.name, request.planDate, request.orders, request.drivers)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@app.delete("/api/plans/{plan_id}")
def plans_delete(plan_id: str) -> dict:
    if not delete_plan(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"status": "deleted", "id": plan_id}


@app.post("/api/export-driver-sheets")
def export_sheets(request: ExportRequest) -> StreamingResponse:
    if not request.orders:
        raise HTTPException(status_code=400, detail="No orders to export")
    plan_date = None
    if request.planDate:
        try:
            plan_date = date.fromisoformat(request.planDate)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid planDate, use YYYY-MM-DD")
    excel_bytes = export_driver_sheets(request.orders, request.drivers, plan_date)
    filename_date = plan_date or date.today()
    filename = f"dispatch-plan-{filename_date.isoformat()}.xlsx"
    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
