"""Sensors for RCEm PV Revenue."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, UPLIFT_MULTIPLIER
from .coordinator import RCEmRevenueCoordinator

CURRENCY_PLN = "PLN"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""

    coordinator: RCEmRevenueCoordinator = entry.runtime_data
    async_add_entities(
        [
            RCEmLatestPublishedPriceSensor(coordinator, entry),
            RCEmSettlementPriceSensor(coordinator, entry),
            PVCurrentMonthRevenueSensor(coordinator, entry),
            PVLifetimeRevenueSensor(coordinator, entry),
        ]
    )


class RCEmSensorBase(CoordinatorEntity[RCEmRevenueCoordinator], SensorEntity):
    """Base sensor entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RCEmRevenueCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "PSE / Home Assistant",
        }
        self.entity_description = SensorEntityDescription(key=key, name=name)


class RCEmLatestPublishedPriceSensor(RCEmSensorBase):
    """Latest published raw RCEm price sensor."""

    _attr_native_unit_of_measurement = f"{CURRENCY_PLN}/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: RCEmRevenueCoordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            "latest_published_price",
            "Latest published price",
        )

    @property
    def native_value(self) -> Decimal | None:
        price = self.coordinator.data.latest_published_price
        if price is None:
            return None
        return price.price_pln_kwh

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        price = self.coordinator.data.latest_published_price
        if price is None:
            return {}
        return {
            "month": price.month,
            "price_pln_mwh": float(price.price_pln_mwh),
            "publication_date": price.publication_date.isoformat()
            if price.publication_date
            else None,
            "corrected": price.corrected,
            "source": price.source,
        }


class RCEmSettlementPriceSensor(RCEmSensorBase):
    """Settlement price including optional uplift."""

    _attr_native_unit_of_measurement = f"{CURRENCY_PLN}/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: RCEmRevenueCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "settlement_price", "Settlement price")

    @property
    def native_value(self) -> Decimal | None:
        price = self.coordinator.data.latest_published_price
        if price is None:
            return None
        return self.coordinator.settlement_price_pln_kwh(price)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        price = self.coordinator.data.latest_published_price
        attributes = {
            "uplift_enabled": self.coordinator.include_23_percent_uplift,
            "uplift_multiplier": UPLIFT_MULTIPLIER
            if self.coordinator.include_23_percent_uplift
            else 1,
        }
        if price is not None:
            attributes["month"] = price.month
            attributes["price_pln_mwh"] = float(price.price_pln_mwh)
            attributes["corrected"] = price.corrected
        return attributes


class PVCurrentMonthRevenueSensor(RCEmSensorBase):
    """Current month PV export revenue."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_PLN
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: RCEmRevenueCoordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            "export_revenue_current_month",
            "Export revenue current month",
        )

    @property
    def native_value(self) -> Decimal | None:
        revenue = self.coordinator.data.current_month_revenue
        if revenue is None:
            return None
        return revenue.revenue_pln

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        revenue = self.coordinator.data.current_month_revenue
        if revenue is None:
            current_month = self.coordinator.data.current_month
            return {
                "month": current_month,
                "price_available": current_month in self.coordinator.data.prices,
                "export_statistics_available": current_month
                not in self.coordinator.data.missing_months,
                "latest_published_month": self.coordinator.data.latest_published_price.month
                if self.coordinator.data.latest_published_price
                else None,
                "missing_months": self.coordinator.data.missing_months,
            }
        return {
            "month": revenue.month,
            "exported_kwh": float(revenue.exported_kwh),
            "price_pln_mwh": float(revenue.price.price_pln_mwh),
            "corrected": revenue.price.corrected,
            "uplift_enabled": self.coordinator.include_23_percent_uplift,
            "missing_months": self.coordinator.data.missing_months,
        }


class PVLifetimeRevenueSensor(RCEmSensorBase):
    """Lifetime PV export revenue from configured start month."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_PLN
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: RCEmRevenueCoordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            "export_revenue_lifetime",
            "Export revenue lifetime",
        )

    @property
    def native_value(self) -> Decimal | None:
        return self.coordinator.data.lifetime_revenue_pln

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "months_calculated": len(self.coordinator.data.monthly_revenue),
            "missing_months": self.coordinator.data.missing_months,
            "uplift_enabled": self.coordinator.include_23_percent_uplift,
        }
