"""SQLite persistence for saved dispatch plans."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .models import DriverCapacity, Order, SavedPlan, SavedPlanSummary

DB_PATH = Path(os.environ.get("PLAN_DB_PATH", "data/plans.db"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                plan_date TEXT NOT NULL,
                orders_json TEXT NOT NULL,
                drivers_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        # Cached geocoder answers (also caches "not found" as NULL lat/lng)
        # so the same address is never looked up twice.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS geocode_cache (
                query_key TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                lat REAL,
                lng REAL,
                label TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        # Consignee address register: one address per recurring consignee.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS address_book (
                id TEXT PRIMARY KEY,
                consignee_key TEXT NOT NULL UNIQUE,
                consignee TEXT NOT NULL,
                address TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def list_plans() -> List[SavedPlanSummary]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, name, plan_date, orders_json, updated_at
            FROM plans
            ORDER BY updated_at DESC
            """
        ).fetchall()
    summaries: List[SavedPlanSummary] = []
    for row in rows:
        orders = json.loads(row["orders_json"])
        summaries.append(
            SavedPlanSummary(
                id=row["id"],
                name=row["name"],
                planDate=row["plan_date"],
                orderCount=len(orders),
                updatedAt=row["updated_at"],
            )
        )
    return summaries


def get_plan(plan_id: str) -> Optional[SavedPlan]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, name, plan_date, orders_json, drivers_json, created_at, updated_at
            FROM plans WHERE id = ?
            """,
            (plan_id,),
        ).fetchone()
    if row is None:
        return None
    return SavedPlan(
        id=row["id"],
        name=row["name"],
        planDate=row["plan_date"],
        orders=[Order(**item) for item in json.loads(row["orders_json"])],
        drivers=[DriverCapacity(**item) for item in json.loads(row["drivers_json"])],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def create_plan(
    name: str,
    plan_date: str,
    orders: List[Order],
    drivers: List[DriverCapacity],
) -> SavedPlan:
    plan_id = str(uuid.uuid4())[:8]
    now = _utc_now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO plans (id, name, plan_date, orders_json, drivers_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id,
                name.strip(),
                plan_date,
                json.dumps([order.model_dump() for order in orders]),
                json.dumps([driver.model_dump() for driver in drivers]),
                now,
                now,
            ),
        )
        conn.commit()
    plan = get_plan(plan_id)
    assert plan is not None
    return plan


def update_plan(
    plan_id: str,
    name: str,
    plan_date: str,
    orders: List[Order],
    drivers: List[DriverCapacity],
) -> Optional[SavedPlan]:
    existing = get_plan(plan_id)
    if existing is None:
        return None
    now = _utc_now()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE plans
            SET name = ?, plan_date = ?, orders_json = ?, drivers_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                name.strip(),
                plan_date,
                json.dumps([order.model_dump() for order in orders]),
                json.dumps([driver.model_dump() for driver in drivers]),
                now,
                plan_id,
            ),
        )
        conn.commit()
    return get_plan(plan_id)


def delete_plan(plan_id: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        conn.commit()
        return cursor.rowcount > 0
