# RCEm PV Revenue

Home Assistant custom integration for estimating Polish prosumer PV export revenue from PSE monthly RCEm prices.

This is a standalone project. It is not related to any other project in this workspace.

## What It Does

- Fetches monthly RCEm prices from PSE:
  `https://www.pse.pl/oire/rcem-rynkowa-miesieczna-cena-energii-elektrycznej`
- Uses the latest corrected RCEm value when PSE publishes one.
- Reads monthly deltas from a cumulative exported energy sensor in Home Assistant.
- Calculates revenue as:
  `exported_kWh * RCEm_PLN_per_MWh / 1000`
- Optionally applies the Polish 23% uplift:
  `exported_kWh * RCEm_PLN_per_MWh * 1.23 / 1000`

The official PSE API endpoint `https://api.raporty.pse.pl/api/rce-pln` exposes interval RCE values in `PLN/MWh`. This integration uses the RCEm webpage for v1 because a dedicated monthly RCEm API endpoint was not found during implementation.

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

Choose a cumulative exported-to-grid energy sensor in `kWh`. It should have long-term statistics enabled, normally:

- `device_class: energy`
- `state_class: total_increasing` or `total`
- `unit_of_measurement: kWh`

The integration reads monthly recorder statistics from that sensor. If statistics are missing for a month, that month is skipped and listed in the revenue sensor attributes.

## Entities

- `sensor.rcem_current_month_price`: raw official RCEm for the current month, in `PLN/kWh`.
- `sensor.rcem_settlement_price`: RCEm after the optional 23% uplift, in `PLN/kWh`.
- `sensor.pv_export_revenue_current_month`: estimated revenue for the current month.
- `sensor.pv_export_revenue_lifetime`: estimated revenue from the configured start month.

RCEm for a month is usually published after that month ends. Until PSE publishes the month, current-month price and revenue may be unavailable.

