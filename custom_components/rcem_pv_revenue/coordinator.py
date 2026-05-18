"""Coordinator for RCEm PV Revenue."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import Any

from aiohttp import ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_EXPORT_ENTITY_ID,
    CONF_INCLUDE_23_PERCENT_UPLIFT,
    CONF_START_MONTH,
    DEFAULT_INCLUDE_23_PERCENT_UPLIFT,
    DEFAULT_START_MONTH,
    DOMAIN,
)
from .rcem import RCEmPrice, async_fetch_rcem_prices
from .revenue import calculate_revenue_pln, settlement_price_pln_kwh
from .statistics import monthly_export_from_statistics

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MonthRevenue:
    """Revenue data for one month."""

    month: str
    exported_kwh: Decimal
    price: RCEmPrice
    revenue_pln: Decimal


@dataclass(frozen=True, slots=True)
class RCEmRevenueData:
    """Coordinator data."""

    prices: dict[str, RCEmPrice]
    monthly_revenue: dict[str, MonthRevenue]
    missing_months: list[str]

    @property
    def current_month(self) -> str:
        return dt_util.now().strftime("%Y-%m")

    @property
    def current_month_price(self) -> RCEmPrice | None:
        return self.prices.get(self.current_month)

    @property
    def current_month_revenue(self) -> MonthRevenue | None:
        return self.monthly_revenue.get(self.current_month)

    @property
    def lifetime_revenue_pln(self) -> Decimal | None:
        if not self.monthly_revenue:
            return None
        return sum(
            (item.revenue_pln for item in self.monthly_revenue.values()),
            Decimal("0"),
        )


class RCEmRevenueCoordinator(DataUpdateCoordinator[RCEmRevenueData]):
    """Fetch PSE prices and Home Assistant export statistics."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""

        self.entry = entry
        self.session: ClientSession = async_get_clientsession(hass)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=24),
        )

    @property
    def export_entity_id(self) -> str:
        """Configured cumulative export energy entity."""

        return self.entry.data[CONF_EXPORT_ENTITY_ID]

    @property
    def include_23_percent_uplift(self) -> bool:
        """Whether settlement revenue includes the 23% uplift."""

        return self.entry.data.get(
            CONF_INCLUDE_23_PERCENT_UPLIFT,
            DEFAULT_INCLUDE_23_PERCENT_UPLIFT,
        )

    async def _async_update_data(self) -> RCEmRevenueData:
        try:
            prices = await async_fetch_rcem_prices(self.session)
            monthly_exports = await self._async_monthly_export_kwh()
        except Exception as err:
            raise UpdateFailed(str(err)) from err

        monthly_revenue: dict[str, MonthRevenue] = {}
        missing_months: list[str] = []
        for month, price in sorted(prices.items()):
            exported = monthly_exports.get(month)
            if exported is None:
                missing_months.append(month)
                continue
            monthly_revenue[month] = MonthRevenue(
                month=month,
                exported_kwh=exported,
                price=price,
                revenue_pln=calculate_revenue_pln(
                    exported,
                    price,
                    self.include_23_percent_uplift,
                ),
            )

        return RCEmRevenueData(
            prices=prices,
            monthly_revenue=monthly_revenue,
            missing_months=missing_months,
        )

    def settlement_price_pln_kwh(self, price: RCEmPrice) -> Decimal:
        """Return configured settlement price for a raw RCEm price."""

        return settlement_price_pln_kwh(price, self.include_23_percent_uplift)

    async def _async_monthly_export_kwh(self) -> dict[str, Decimal]:
        """Read monthly export deltas from HA recorder statistics."""

        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.statistics import (
                statistics_during_period,
            )
        except ImportError as err:
            _LOGGER.debug("Recorder statistics unavailable: %s", err)
            return {}

        start = _month_start(
            self.entry.data.get(CONF_START_MONTH, DEFAULT_START_MONTH)
        )
        end = dt_util.now()

        def _read_stats() -> dict[str, Any]:
            return statistics_during_period(
                self.hass,
                start,
                end,
                statistic_ids={self.export_entity_id},
                period="month",
                units={"energy": "kWh"},
                types={"change", "state", "sum"},
            )

        stats = await get_instance(self.hass).async_add_executor_job(_read_stats)
        rows = stats.get(self.export_entity_id) or []
        return monthly_export_from_statistics(rows)


def _month_start(month: str) -> datetime:
    year, month_number = (int(part) for part in month.split("-", 1))
    return dt_util.start_of_local_day(datetime(year, month_number, 1))
