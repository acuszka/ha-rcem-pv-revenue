from decimal import Decimal

from custom_components.rcem_pv_revenue.rcem import RCEmPrice
from custom_components.rcem_pv_revenue.revenue import (
    calculate_revenue_pln,
    settlement_price_pln_kwh,
)


def test_calculate_revenue_without_uplift() -> None:
    price = RCEmPrice(
        month="2024-01",
        price_pln_mwh=Decimal("437.02"),
        publication_date=None,
        corrected=False,
    )

    assert settlement_price_pln_kwh(price, False) == Decimal("0.43702")
    assert calculate_revenue_pln("100.5", price, False) == Decimal("43.92")


def test_calculate_revenue_with_23_percent_uplift() -> None:
    price = RCEmPrice(
        month="2024-01",
        price_pln_mwh=Decimal("437.02"),
        publication_date=None,
        corrected=False,
    )

    assert settlement_price_pln_kwh(price, True) == Decimal("0.53753")
    assert calculate_revenue_pln("100.5", price, True) == Decimal("54.02")

