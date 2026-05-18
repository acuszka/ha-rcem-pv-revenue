"""Revenue calculations for RCEm PV Revenue."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .const import UPLIFT_MULTIPLIER
from .rcem import RCEmPrice

MONEY_QUANT = Decimal("0.01")
PRICE_QUANT = Decimal("0.00001")


def settlement_price_pln_kwh(
    price: RCEmPrice,
    include_23_percent_uplift: bool,
) -> Decimal:
    """Return the PLN/kWh settlement price, optionally increased by 23%."""

    value = price.price_pln_kwh
    if include_23_percent_uplift:
        value *= Decimal(str(UPLIFT_MULTIPLIER))
    return value.quantize(PRICE_QUANT, rounding=ROUND_HALF_UP)


def calculate_revenue_pln(
    exported_kwh: Decimal | float | int | str,
    price: RCEmPrice,
    include_23_percent_uplift: bool,
) -> Decimal:
    """Calculate revenue from exported kWh and RCEm."""

    energy = Decimal(str(exported_kwh))
    value = energy * settlement_price_pln_kwh(price, include_23_percent_uplift)
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

