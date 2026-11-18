"""Consignee address register.

Many consignees recur every day. The planner stores each consignee's
delivery address once; future orders with the same consignee get the
address filled in automatically (when the daily sheet has none).
"""

from __future__ import annotations

import re
import uuid
from typing import List, Optional

from . import plan_storage
from .consignee_parser import _NOISE_RE, _PHONE_RE, _fold
from .models import AddressBookEntry, Order


def consignee_key(consignee: str) -> str:
    """Normalize consignee text for matching: case/accents/phones/codes ignored."""
    text = _PHONE_RE.sub(" ", consignee)
    text = _NOISE_RE.sub("", text)
    text = _fold(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _row_to_entry(row) -> AddressBookEntry:
    return AddressBookEntry(
        id=row["id"],
        consignee=row["consignee"],
        address=row["address"],
        updatedAt=row["updated_at"],
    )


def list_entries() -> List[AddressBookEntry]:
    with plan_storage._connect() as conn:
        rows = conn.execute(
            "SELECT id, consignee, address, updated_at FROM address_book ORDER BY consignee COLLATE NOCASE"
        ).fetchall()
    return [_row_to_entry(row) for row in rows]


def upsert_entry(consignee: str, address: str) -> AddressBookEntry:
    """Create or replace the address for a consignee (matched by normalized name)."""
    key = consignee_key(consignee)
    if not key:
        raise ValueError("Consignee is required")
    if not address.strip():
        raise ValueError("Address is required")
    now = plan_storage._utc_now()
    with plan_storage._connect() as conn:
        existing = conn.execute(
            "SELECT id FROM address_book WHERE consignee_key = ?", (key,)
        ).fetchone()
        entry_id = existing["id"] if existing else str(uuid.uuid4())[:8]
        conn.execute(
            """
            INSERT INTO address_book (id, consignee_key, consignee, address, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(consignee_key) DO UPDATE SET
                consignee = excluded.consignee,
                address = excluded.address,
                updated_at = excluded.updated_at
            """,
            (entry_id, key, consignee.strip(), address.strip(), now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, consignee, address, updated_at FROM address_book WHERE id = ?",
            (entry_id,),
        ).fetchone()
    return _row_to_entry(row)


def update_entry(entry_id: str, consignee: str, address: str) -> Optional[AddressBookEntry]:
    key = consignee_key(consignee)
    if not key or not address.strip():
        raise ValueError("Consignee and address are required")
    with plan_storage._connect() as conn:
        clash = conn.execute(
            "SELECT id FROM address_book WHERE consignee_key = ? AND id != ?",
            (key, entry_id),
        ).fetchone()
        if clash:
            raise ValueError("Another entry already exists for this consignee")
        cursor = conn.execute(
            """
            UPDATE address_book
            SET consignee_key = ?, consignee = ?, address = ?, updated_at = ?
            WHERE id = ?
            """,
            (key, consignee.strip(), address.strip(), plan_storage._utc_now(), entry_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        row = conn.execute(
            "SELECT id, consignee, address, updated_at FROM address_book WHERE id = ?",
            (entry_id,),
        ).fetchone()
    return _row_to_entry(row)


def delete_entry(entry_id: str) -> bool:
    with plan_storage._connect() as conn:
        cursor = conn.execute("DELETE FROM address_book WHERE id = ?", (entry_id,))
        conn.commit()
        return cursor.rowcount > 0


def apply_address_book(orders: List[Order]) -> int:
    """Fill empty order addresses from the register. Returns how many were filled."""
    with plan_storage._connect() as conn:
        rows = conn.execute("SELECT consignee_key, address FROM address_book").fetchall()
    book = {row["consignee_key"]: row["address"] for row in rows}
    if not book:
        return 0
    filled = 0
    for order in orders:
        if order.address.strip():
            continue
        address = book.get(consignee_key(order.consignee))
        if address:
            order.address = address
            order.lat = order.lng = None
            order.geocodePrecision = None
            filled += 1
    return filled
