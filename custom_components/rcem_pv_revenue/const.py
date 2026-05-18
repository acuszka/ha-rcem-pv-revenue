"""Constants for the RCEm PV Revenue integration."""

from __future__ import annotations

DOMAIN = "rcem_pv_revenue"

CONF_EXPORT_ENTITY_ID = "export_entity_id"
CONF_EXPORT_STATISTIC_ID = "export_statistic_id"
CONF_START_MONTH = "start_month"
CONF_INCLUDE_23_PERCENT_UPLIFT = "include_23_percent_uplift"
OPTION_LAST_NOTIFIED_MONTH = "last_notified_month"

DEFAULT_INCLUDE_23_PERCENT_UPLIFT = True
DEFAULT_START_MONTH = "2022-06"

PSE_RCEM_URL = (
    "https://www.pse.pl/oire/"
    "rcem-rynkowa-miesieczna-cena-energii-elektrycznej"
)

UPLIFT_MULTIPLIER = 1.23
