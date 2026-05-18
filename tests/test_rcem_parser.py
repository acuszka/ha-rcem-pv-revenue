from datetime import date
from decimal import Decimal

from custom_components.rcem_pv_revenue.rcem import parse_rcem_html


def test_parse_original_and_latest_corrected_rcem() -> None:
    html = """
    <html><body>
      <h2>2024</h2>
      <table>
        <tr><td>styczeń</td></tr>
        <tr><td>RCEm</td><td>437,02</td><td>11.02.2024</td><td>-</td></tr>
        <tr><td>luty</td></tr>
        <tr><td>RCEm</td><td>324,25</td><td>11.03.2024</td><td>-</td></tr>
        <tr><td>skorygowana RCEm*</td><td>323,17</td><td>11.06.2024</td><td>-0,33</td></tr>
        <tr><td>skorygowana RCEm*</td><td>322,10</td><td>11.07.2024</td><td>-0,66</td></tr>
      </table>
      <h2>2023</h2>
      <table>
        <tr><td>grudzień</td></tr>
        <tr><td>RCEm</td><td>304,63</td><td>11.01.2024</td><td>-</td></tr>
      </table>
    </body></html>
    """

    prices = parse_rcem_html(html)

    assert prices["2024-01"].price_pln_mwh == Decimal("437.02")
    assert prices["2024-01"].corrected is False
    assert prices["2024-02"].price_pln_mwh == Decimal("322.10")
    assert prices["2024-02"].publication_date == date(2024, 7, 11)
    assert prices["2024-02"].corrected is True
    assert prices["2023-12"].price_pln_kwh == Decimal("0.30463")


def test_parse_plain_text_like_pse_rendered_page() -> None:
    html = """
    2025
    marzec
    RCEm 278,50 11.04.2025 -
    kwiecień
    RCEm 301.25 11.05.2025 -
    """

    prices = parse_rcem_html(html)

    assert prices["2025-03"].price_pln_mwh == Decimal("278.50")
    assert prices["2025-04"].price_pln_mwh == Decimal("301.25")

