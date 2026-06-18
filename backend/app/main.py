"""FastAPI application for the Sampo dispatch planning demo."""

from datetime import date
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .excel_service import export_driver_sheets, parse_orders_from_excel
from .models import ExportRequest, Order, PlanRequest, PlanResponse
from .planning_service import calculate_plan
from .sample_data import get_sample_orders

app = FastAPI(title="Sampo Dispatch Planning Demo", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


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
    return orders


@app.get("/api/sample-orders", response_model=List[Order])
def sample_orders() -> List[Order]:
    return get_sample_orders()


@app.post("/api/calculate-plan", response_model=PlanResponse)
def calculate(request: PlanRequest) -> PlanResponse:
    orders, summaries = calculate_plan(request.orders, request.drivers)
    return PlanResponse(orders=orders, routeSummaries=summaries)


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
