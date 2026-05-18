from datetime import datetime, timezone
from decimal import Decimal

from custom_components.rcem_pv_revenue.statistics import monthly_export_from_statistics


def test_monthly_export_from_change_statistics() -> None:
    rows = [
        {"start": datetime(2024, 1, 1, tzinfo=timezone.utc), "change": 10.5},
        {"start": datetime(2024, 2, 1, tzinfo=timezone.utc), "change": 12},
    ]

    assert monthly_export_from_statistics(rows) == {
        "2024-01": Decimal("10.5"),
        "2024-02": Decimal("12"),
    }


def test_monthly_export_falls_back_to_state_delta() -> None:
    rows = [
        {"start": datetime(2024, 1, 1, tzinfo=timezone.utc), "state": 100},
        {"start": datetime(2024, 2, 1, tzinfo=timezone.utc), "state": 135.25},
    ]

    assert monthly_export_from_statistics(rows) == {
        "2024-02": Decimal("35.25"),
    }


def test_monthly_export_falls_back_to_sum_delta() -> None:
    rows = [
        {"start": datetime(2024, 1, 1, tzinfo=timezone.utc), "sum": 100},
        {"start": datetime(2024, 2, 1, tzinfo=timezone.utc), "sum": 135.25},
    ]

    assert monthly_export_from_statistics(rows) == {
        "2024-02": Decimal("35.25"),
    }
