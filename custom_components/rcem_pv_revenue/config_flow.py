"""Config flow for RCEm PV Revenue."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_EXPORT_ENTITY_ID,
    CONF_INCLUDE_23_PERCENT_UPLIFT,
    CONF_START_MONTH,
    DEFAULT_INCLUDE_23_PERCENT_UPLIFT,
    DEFAULT_START_MONTH,
    DOMAIN,
)


class RCEmRevenueConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an RCEm PV Revenue config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            start_month = user_input[CONF_START_MONTH]
            if not _valid_month(start_month):
                errors[CONF_START_MONTH] = "invalid_month"
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or "RCEm PV Revenue",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="RCEm PV Revenue"): str,
                vol.Required(CONF_EXPORT_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor"),
                ),
                vol.Optional(CONF_START_MONTH, default=DEFAULT_START_MONTH): str,
                vol.Optional(
                    CONF_INCLUDE_23_PERCENT_UPLIFT,
                    default=DEFAULT_INCLUDE_23_PERCENT_UPLIFT,
                ): bool,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


def _valid_month(value: str) -> bool:
    try:
        year, month = value.split("-", 1)
        return len(year) == 4 and len(month) == 2 and 1 <= int(month) <= 12
    except (AttributeError, ValueError):
        return False
