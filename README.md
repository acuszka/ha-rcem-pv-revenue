# RCEm PV Revenue

Home Assistant custom integration for estimating Polish prosumer PV export revenue from PSE monthly RCEm prices.

## Features

- Fetches monthly RCEm prices from PSE.
- Uses corrected RCEm values when PSE publishes them.
- Calculates export revenue from Home Assistant energy statistics.
- Optional 23% uplift for Polish prosumer settlement.
- Home Assistant notification when PSE publishes a new monthly RCEm.
- Sensors for current month, previous month, current year, and configured lifetime revenue.

Revenue formula:

```text
exported_kWh * RCEm_PLN_per_MWh * multiplier / 1000
```

where `multiplier` is `1.23` when the uplift option is enabled.

## Installation

In HACS, add this repository as a custom repository of type **Integration**:

```text
https://github.com/acuszka/ha-rcem-pv-revenue
```

Install **RCEm PV Revenue**, restart Home Assistant, then add the integration from **Settings -> Devices & services**.

## Input Statistic

Select an exported-to-grid energy sensor in `kWh`, or enter a recorder statistic ID used by the Energy dashboard.

For Tauron AMIplus users, the useful Energy dashboard statistic may look like:

```text
tauron_importer:<your_customer_id>_balanced_generation
```

## Main Entities

- `sensor.rcem_pv_revenue_latest_published_price`
- `sensor.rcem_pv_revenue_settlement_price`
- `sensor.rcem_pv_revenue_export_revenue_current_month`
- `sensor.rcem_pv_revenue_export_revenue_previous_month`
- `sensor.rcem_pv_revenue_export_revenue_current_year`
- `sensor.rcem_pv_revenue_export_revenue_since_yyyy_mm`

Current-month revenue can be unavailable until PSE publishes RCEm for that month.

## Monthly Dashboard

The current-year and lifetime revenue sensors expose `monthly_breakdown`.

Markdown card:

```jinja
| Month | Export | Revenue |
|---|---:|---:|
{% for row in state_attr('sensor.rcem_pv_revenue_export_revenue_current_year', 'monthly_breakdown') or [] -%}
| {{ row.month }} | {{ row.exported_kwh | round(1) }} kWh | {{ row.revenue_pln | round(2) }} PLN |
{% endfor %}
```

ApexCharts Card:

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: PV Export Revenue By Month
graph_span: 1year
span:
  start: year
apex_config:
  chart:
    type: bar
    height: 260
    toolbar:
      show: false
  plotOptions:
    bar:
      borderRadius: 4
      columnWidth: 48%
  fill:
    type: gradient
    gradient:
      type: vertical
      gradientToColors:
        - '#f59e0b'
      opacityFrom: 0.95
      opacityTo: 0.65
  xaxis:
    type: datetime
  yaxis:
    title:
      text: PLN
    min: 0
series:
  - entity: sensor.rcem_pv_revenue_export_revenue_current_year
    name: Revenue
    unit: PLN
    type: column
    color: '#facc15'
    data_generator: |
      const breakdown = entity.attributes.monthly_breakdown || [];
      return breakdown
        .filter((row) => Number(row.revenue_pln || 0) > 0)
        .map((row) => [new Date(`${row.month}-01T12:00:00`).getTime(), Number(row.revenue_pln || 0)]);
```
