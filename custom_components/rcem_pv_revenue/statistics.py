"""Helpers for Home Assistant recorder statistics rows."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def monthly_export_from_statistics(rows: list[dict[str, Any]]) -> dict[str, Decimal]:
    """Convert recorder monthly rows into month -> kWh deltas."""

    result: dict[str, Decimal] = {}
    previous_state: Decimal | None = None

    for row in rows:
        month = month_from_row(row)
        if month is None:
            continue

        change = decimal_or_none(row.get("change"))
        if change is not None:
            result[month] = max(change, Decimal("0"))
            previous_state = decimal_or_none(row.get("state")) or previous_state
            continue

        state = decimal_or_none(row.get("state"))
        if state is None:
            state = decimal_or_none(row.get("sum"))
        if state is None:
            continue
        if previous_state is not None:
            result[month] = max(state - previous_state, Decimal("0"))
        previous_state = state

    return result


def month_from_row(row: dict[str, Any]) -> str | None:
    """Extract YYYY-MM from a recorder statistics row."""

    start = row.get("start")
    if start is None:
        return None
    if isinstance(start, (int, float)):
        timestamp = start / 1000 if start > 10_000_000_000 else start
        dt = datetime.fromtimestamp(timestamp).astimezone()
    elif isinstance(start, datetime):
        dt = start.astimezone()
    else:
        try:
            dt = datetime.fromisoformat(str(start))
        except (TypeError, ValueError):
            return None
        dt = dt.astimezone() if dt.tzinfo else dt
    return dt.strftime("%Y-%m")


def decimal_or_none(value: Any) -> Decimal | None:
    """Convert a value to Decimal, returning None for invalid input."""

    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
