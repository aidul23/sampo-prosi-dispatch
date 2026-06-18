"""Excel import/export for the dispatch planning demo."""

import io
import uuid
from typing import List, Optional

import pandas as pd

from .models import DriverCapacity, Order, RouteSummary
from .planning_service import calculate_plan, fin_equivalent

# Header aliases (lowercased) -> order field.
HEADER_ALIASES = {
    "customer": "customer",
    "asiakas": "customer",
    "lähettäjä": "customer",
    "lahettaja": "customer",
    "pickup driver": "pickupDriver",
    "noutokuljettaja": "pickupDriver",
    "noutaja": "pickupDriver",
    "consignee": "consignee",
    "vastaanottaja": "consignee",
    "pallets": "pallets",
    "lavat": "pallets",
    "extra info": "extraInfo",
    "lisätieto": "extraInfo",
    "lisatieto": "extraInfo",
    "delivery driver": "deliveryDriver",
    "jakokuljettaja": "deliveryDriver",
    "kuski": "deliveryDriver",
    "pallet type": "palletType",
    "lavatyyppi": "palletType",
    "stackable": "stackable",
    "pinottava": "stackable",
    "route area": "routeArea",
    "reittialue": "routeArea",
    "status": "status",
    "tila": "status",
}

# Fallback mapping by column position (A..F) when headers are not recognised.
POSITION_FIELDS = [
    "customer",
    "pickupDriver",
    "consignee",
    "pallets",
    "extraInfo",
    "deliveryDriver",
]


def _clean_str(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _parse_pallets(value) -> float:
    try:
        num = float(str(value).replace(",", "."))
        return num if num >= 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def _parse_bool(value) -> bool:
    return _clean_str(value).lower() in {"true", "yes", "kyllä", "kylla", "x", "1", "1.0"}


HEADER_SCAN_ROWS = 15


def _find_header_row(df: pd.DataFrame) -> Optional[tuple[int, dict]]:
    """Scan the first rows for one containing at least two known header names.

    Real customer sheets often have title/date rows above the actual header row.
    Returns (row_index, {column_index: field}) or None.
    """
    for row_idx in range(min(HEADER_SCAN_ROWS, len(df))):
        mapping = {}
        for col_idx, value in enumerate(df.iloc[row_idx]):
            field = HEADER_ALIASES.get(_clean_str(value).lower())
            if field and field not in mapping.values():
                mapping[col_idx] = field
        if len(mapping) >= 2:
            return row_idx, mapping
    return None


def _fill_unmapped_by_position(mapping: dict) -> dict:
    """Assign positional fields (A..F) to columns the header row left unnamed.

    E.g. the customer's sheet names A/C/D/F but leaves B (pickup driver) and
    E (extra info) without headers.
    """
    mapping = dict(mapping)
    for col_idx, field in enumerate(POSITION_FIELDS):
        if col_idx not in mapping and field not in mapping.values():
            mapping[col_idx] = field
    return mapping


def parse_orders_from_excel(file_bytes: bytes) -> List[Order]:
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, header=None)

    found = _find_header_row(df)
    if found is not None:
        header_idx, mapping = found
        mapping = _fill_unmapped_by_position(mapping)
        df = df.iloc[header_idx + 1 :]
    else:
        # No recognisable headers anywhere: map purely by column position.
        mapping = {i: field for i, field in enumerate(POSITION_FIELDS)}

    mapping = {col: field for col, field in mapping.items() if col < df.shape[1]}

    orders: List[Order] = []
    last_customer = ""
    for _, row in df.iterrows():
        raw = {field: row.iloc[col] for col, field in mapping.items()}
        if all(_clean_str(v) == "" for v in raw.values()):
            continue

        # Grouped rows: customer is written once and left empty on the
        # following rows of the same group. Inherit it from above.
        customer = _clean_str(raw.get("customer"))
        if customer:
            last_customer = customer
        elif _clean_str(raw.get("consignee")):
            customer = last_customer
        raw["customer"] = customer

        pallet_type = _clean_str(raw.get("palletType")).upper()
        if pallet_type not in {"FIN", "EUR", "OTHER"}:
            pallet_type = "FIN"

        status = _clean_str(raw.get("status")).upper().replace(" ", "_")
        if status not in {"NEW", "PLANNED", "DELIVERED", "CARRY_OVER"}:
            status = "NEW"

        order = Order(
            id=str(uuid.uuid4())[:8],
            customer=_clean_str(raw.get("customer")),
            pickupDriver=_clean_str(raw.get("pickupDriver")),
            consignee=_clean_str(raw.get("consignee")),
            pallets=_parse_pallets(raw.get("pallets")),
            palletType=pallet_type,
            stackable=_parse_bool(raw.get("stackable")),
            extraInfo=_clean_str(raw.get("extraInfo")),
            deliveryDriver=_clean_str(raw.get("deliveryDriver")),
            routeArea=_clean_str(raw.get("routeArea")),
            status=status,
        )
        order.finEquivalent = fin_equivalent(order.pallets, order.palletType, order.stackable)
        orders.append(order)

    return orders


ORDER_COLUMNS = [
    ("customer", "Customer"),
    ("pickupDriver", "Pickup Driver"),
    ("consignee", "Consignee"),
    ("pallets", "Pallets"),
    ("palletType", "Pallet Type"),
    ("stackable", "Stackable"),
    ("extraInfo", "Extra Info"),
    ("deliveryDriver", "Delivery Driver"),
    ("routeArea", "Route Area"),
    ("status", "Status"),
    ("finEquivalent", "FIN Equivalent"),
    ("warning", "Warning"),
]


def _orders_to_dataframe(orders: List[Order]) -> pd.DataFrame:
    rows = []
    for order in orders:
        data = order.model_dump()
        rows.append({label: data[field] for field, label in ORDER_COLUMNS})
    return pd.DataFrame(rows, columns=[label for _, label in ORDER_COLUMNS])


def _summaries_to_dataframe(summaries: List[RouteSummary]) -> pd.DataFrame:
    rows = [
        {
            "Driver": s.driverName,
            "Capacity": s.capacity,
            "Used Capacity": s.usedCapacity,
            "Remaining Capacity": s.remainingCapacity,
            "Orders": s.ordersCount,
            "Overloaded": "YES" if s.overloaded else "no",
        }
        for s in summaries
    ]
    return pd.DataFrame(rows)


def _safe_sheet_name(name: str) -> str:
    cleaned = "".join(c for c in name if c not in "[]:*?/\\").strip() or "Unassigned"
    return cleaned[:31]


def _format_plan_title(plan_date) -> str:
    """Format like the customer's Excel: e.g. Tiistai 28.4.2026."""
    fi_days = [
        "Maanantai",
        "Tiistai",
        "Keskiviikko",
        "Torstai",
        "Perjantai",
        "Lauantai",
        "Sunnuntai",
    ]
    return f"{fi_days[plan_date.weekday()]} {plan_date.day}.{plan_date.month}.{plan_date.year}"


def _write_sheet_with_title(
    writer: pd.ExcelWriter,
    sheet_name: str,
    df: pd.DataFrame,
    plan_title: Optional[str],
) -> None:
    startrow = 2 if plan_title else 0
    df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=startrow)
    if plan_title:
        writer.sheets[sheet_name]["A1"] = plan_title


def export_driver_sheets(
    orders: List[Order],
    drivers: List[DriverCapacity],
    plan_date=None,
) -> bytes:
    """Build a workbook: Full Plan, one sheet per driver, Route Summary."""
    orders, summaries = calculate_plan(orders, drivers)
    plan_title = _format_plan_title(plan_date) if plan_date else None

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _write_sheet_with_title(
            writer, "Full Plan", _orders_to_dataframe(orders), plan_title
        )

        drivers_in_plan = sorted({o.deliveryDriver.strip() for o in orders if o.deliveryDriver.strip()})
        for driver in drivers_in_plan:
            driver_orders = [o for o in orders if o.deliveryDriver.strip() == driver]
            _write_sheet_with_title(
                writer,
                _safe_sheet_name(driver),
                _orders_to_dataframe(driver_orders),
                plan_title,
            )

        unassigned = [o for o in orders if not o.deliveryDriver.strip()]
        if unassigned:
            _write_sheet_with_title(
                writer, "Unassigned", _orders_to_dataframe(unassigned), plan_title
            )

        _write_sheet_with_title(
            writer, "Route Summary", _summaries_to_dataframe(summaries), plan_title
        )

    buffer.seek(0)
    return buffer.read()
