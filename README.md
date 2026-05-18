# RCEm PV Revenue

Home Assistant custom integration for estimating Polish prosumer PV export revenue from PSE monthly RCEm prices.

## What It Does

- Fetches monthly RCEm prices from PSE:
  `https://www.pse.pl/oire/rcem-rynkowa-miesieczna-cena-energii-elektrycznej`
- Uses the latest corrected RCEm value when PSE publishes one.
- Reads monthly deltas from a cumulative exported energy sensor in Home Assistant.
- Calculates revenue as:
  `exported_kWh * RCEm_PLN_per_MWh / 1000`
- Optionally applies the Polish 23% uplift:
  `exported_kWh * RCEm_PLN_per_MWh * 1.23 / 1000`

## Installation

### HACS Custom Repository

1. Copy or publish this repository to GitHub.
2. In HACS, add it as a custom repository of type `Integration`.
3. Install `RCEm PV Revenue`.
4. Restart Home Assistant.
5. Add the integration from Settings -> Devices & services.

### Manual

Copy `custom_components/rcem_pv_revenue` into your Home Assistant `custom_components` directory and restart Home Assistant.

## Required Input Sensor

Choose a cumulative exported-to-grid energy sensor in `kWh`, or enter the recorder statistic ID used by the Energy dashboard. Some integrations expose Energy dashboard sources only as statistic IDs, not as entities in Developer Tools -> States.

For example, if Energy dashboard uses:

```text
tauron_importer:**************_balanced_generation
```

enter your full value as **Exported energy statistic ID**. For Tauron users this value may come from the HACS integration **Tauron AMIplus**. Use the monthly balanced generation statistic from Tauron AMIplus, for example `tauron_importer:<your_customer_id>_balanced_generation`.

If you choose an entity, it should have long-term statistics enabled, normally:

- `device_class: energy`
- `state_class: total_increasing` or `total`
- `unit_of_measurement: kWh`

The integration reads monthly recorder statistics from that sensor. If statistics are missing for a month, that month is skipped and listed in the revenue sensor attributes.

## Entities

- `sensor.rcem_latest_published_price`: latest raw official RCEm published by PSE, in `PLN/kWh`.
- `sensor.rcem_settlement_price`: latest RCEm after the optional 23% uplift, in `PLN/kWh`.
- `sensor.pv_export_revenue_current_month`: estimated revenue for the current month.
- `sensor.pv_export_revenue_previous_month`: estimated revenue for the previous month.
- `sensor.pv_export_revenue_current_year`: estimated revenue for the current year.
- `sensor.pv_export_revenue_lifetime`: estimated revenue from the configured start month.

RCEm for a month is usually published after that month ends. Until PSE publishes the month, current-month price and revenue may be unavailable.

The lifetime and current-year sensors expose diagnostic attributes including `total_exported_kwh` and `monthly_breakdown`. Use those to verify that the selected entity or statistic ID represents exported-to-grid energy, not total PV generation.

## Showing Monthly Revenue On A Dashboard

The integration exposes month-by-month data through the `monthly_breakdown` attribute on the lifetime and current-year revenue sensors. This avoids creating a growing number of separate monthly entities.

A simple built-in option is a Markdown card:

```jinja
| Month | Export | Revenue |
|---|---:|---:|
{% for row in state_attr('sensor.pv_export_revenue_current_year', 'monthly_breakdown') or [] -%}
| {{ row.month }} | {{ row.exported_kwh | round(1) }} kWh | {{ row.revenue_pln | round(2) }} PLN |
{% endfor %}
```

For charts, use a dashboard card that can read attributes, such as ApexCharts Card, and point it at the same `monthly_breakdown` attribute.
