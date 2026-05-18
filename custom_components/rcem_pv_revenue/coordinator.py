"""Coordinator for RCEm PV Revenue."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import Any

from aiohttp import ClientSession

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_EXPORT_ENTITY_ID,
    CONF_EXPORT_STATISTIC_ID,
    CONF_INCLUDE_23_PERCENT_UPLIFT,
    CONF_START_MONTH,
    DEFAULT_INCLUDE_23_PERCENT_UPLIFT,
    DEFAULT_START_MONTH,
    DOMAIN,
    OPTION_LAST_NOTIFIED_MONTH,
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
    def previous_month(self) -> str:
        first_day_this_month = dt_util.now().replace(day=1)
        previous = first_day_this_month - timedelta(days=1)
        return previous.strftime("%Y-%m")

    @property
    def current_month_price(self) -> RCEmPrice | None:
        return self.prices.get(self.current_month)

    @property
    def latest_published_price(self) -> RCEmPrice | None:
        if not self.prices:
            return None
        return self.prices[max(self.prices)]

    @property
    def current_month_revenue(self) -> MonthRevenue | None:
        return self.monthly_revenue.get(self.current_month)

    @property
    def previous_month_revenue(self) -> MonthRevenue | None:
        return self.monthly_revenue.get(self.previous_month)

    @property
    def current_year(self) -> str:
        return dt_util.now().strftime("%Y")

    @property
    def current_year_revenue_pln(self) -> Decimal | None:
        items = [
            item
            for month, item in self.monthly_revenue.items()
            if month.startswith(f"{self.current_year}-")
        ]
        if not items:
            return None
        return sum((item.revenue_pln for item in items), Decimal("0"))

    @property
    def current_year_exported_kwh(self) -> Decimal | None:
        items = [
            item
            for month, item in self.monthly_revenue.items()
            if month.startswith(f"{self.current_year}-")
        ]
        if not items:
            return None
        return sum((item.exported_kwh for item in items), Decimal("0"))

    @property
    def lifetime_exported_kwh(self) -> Decimal | None:
        if not self.monthly_revenue:
            return None
        return sum(
            (item.exported_kwh for item in self.monthly_revenue.values()),
            Decimal("0"),
        )

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
        """Configured cumulative export energy entity, if any."""

        return self.entry.data.get(CONF_EXPORT_ENTITY_ID, "")

    @property
    def export_statistic_id(self) -> str:
        """Configured recorder statistic id."""

        return self.entry.data.get(CONF_EXPORT_STATISTIC_ID) or self.export_entity_id

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

        data = RCEmRevenueData(
            prices=prices,
            monthly_revenue=monthly_revenue,
            missing_months=missing_months,
        )
        self._notify_new_monthly_price(data)
        return data

    def settlement_price_pln_kwh(self, price: RCEmPrice) -> Decimal:
        """Return configured settlement price for a raw RCEm price."""

        return settlement_price_pln_kwh(price, self.include_23_percent_uplift)

    def _notify_new_monthly_price(self, data: RCEmRevenueData) -> None:
        """Create an HA notification when PSE publishes a new monthly RCEm."""

        latest_price = data.latest_published_price
        if latest_price is None:
            return

        latest_month = latest_price.month
        last_notified_month = self.entry.options.get(OPTION_LAST_NOTIFIED_MONTH)

        if last_notified_month is None:
            self.hass.config_entries.async_update_entry(
                self.entry,
                options={
                    **self.entry.options,
                    OPTION_LAST_NOTIFIED_MONTH: latest_month,
                },
            )
            return

        if latest_month <= last_notified_month:
            return

        settlement_price = self.settlement_price_pln_kwh(latest_price)
        persistent_notification.async_create(
            self.hass,
            (
                f"PSE published RCEm for {latest_month}: "
                f"{latest_price.price_pln_mwh} PLN/MWh "
                f"({settlement_price} PLN/kWh settlement price)."
            ),
            title="New RCEm price published",
            notification_id=f"{DOMAIN}_new_price_{latest_month}",
        )
        self.hass.config_entries.async_update_entry(
            self.entry,
            options={
                **self.entry.options,
                OPTION_LAST_NOTIFIED_MONTH: latest_month,
            },
        )

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
                statistic_ids={self.export_statistic_id},
                period="month",
                units={"energy": "kWh"},
                types={"change", "state", "sum"},
            )

        stats = await get_instance(self.hass).async_add_executor_job(_read_stats)
        rows = stats.get(self.export_statistic_id) or []
        _LOGGER.debug(
            "Loaded %s recorder statistic rows for %s",
            len(rows),
            self.export_statistic_id,
        )
        return monthly_export_from_statistics(rows)


def _month_start(month: str) -> datetime:
    year, month_number = (int(part) for part in month.split("-", 1))
    return dt_util.start_of_local_day(datetime(year, month_number, 1))
