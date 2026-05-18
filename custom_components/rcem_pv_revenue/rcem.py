"""Fetch and parse official PSE RCEm prices."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp import ClientSession

from .const import PSE_RCEM_URL

MONTHS_PL = {
    "styczen": 1,
    "styczeń": 1,
    "luty": 2,
    "marzec": 3,
    "kwiecien": 4,
    "kwiecień": 4,
    "maj": 5,
    "czerwiec": 6,
    "lipiec": 7,
    "sierpien": 8,
    "sierpień": 8,
    "wrzesien": 9,
    "wrzesień": 9,
    "pazdziernik": 10,
    "październik": 10,
    "listopad": 11,
    "grudzien": 12,
    "grudzień": 12,
}

YEAR_RE = re.compile(r"^(20\d{2})$")
PRICE_RE = re.compile(r"(-?\d{1,5},\d{1,5}|-?\d{1,5}\.\d{1,5})")
DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(20\d{2})")


@dataclass(frozen=True, slots=True)
class RCEmPrice:
    """A monthly RCEm price entry."""

    month: str
    price_pln_mwh: Decimal
    publication_date: date | None
    corrected: bool
    source: str = PSE_RCEM_URL

    @property
    def price_pln_kwh(self) -> Decimal:
        """Return the price converted from PLN/MWh to PLN/kWh."""

        return self.price_pln_mwh / Decimal("1000")


class _TextExtractor(HTMLParser):
    """Extract text fragments from HTML while preserving table cell breaks."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        for raw_line in data.replace("\xa0", " ").splitlines():
            text = " ".join(raw_line.split())
            if text:
                self.parts.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"tr", "td", "th", "br", "p", "div", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"tr", "td", "th", "p", "div", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def text(self) -> str:
        return "\n".join(part for part in self.parts if part.strip())


def _parse_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None


def _parse_publication_date(text: str) -> date | None:
    match = DATE_RE.search(text)
    if not match:
        return None
    day, month, year = (int(group) for group in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _normalize_token(text: str) -> str:
    return " ".join(text.lower().replace("\xa0", " ").split())


def parse_rcem_html(html: str, source: str = PSE_RCEM_URL) -> dict[str, RCEmPrice]:
    """Parse PSE's RCEm HTML page and return latest price per month.

    PSE publishes original RCEm rows and may later add corrected RCEm rows.
    For each month, the latest row encountered on the page wins. The official
    page orders corrections under their month, so this gives the newest
    corrected value where available while preserving original values otherwise.
    """

    parser = _TextExtractor()
    parser.feed(html)
    lines = [_normalize_token(line) for line in parser.text().splitlines()]

    prices: dict[str, RCEmPrice] = {}
    current_year: int | None = None
    current_month_number: int | None = None

    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line:
            continue

        year_match = YEAR_RE.match(line)
        if year_match:
            current_year = int(year_match.group(1))
            current_month_number = None
            continue

        month_label = line.rstrip("*")
        if month_label in MONTHS_PL:
            current_month_number = MONTHS_PL[month_label]
            continue

        if current_year is None or current_month_number is None:
            continue

        is_original = line == "rcem" or line.startswith("rcem ")
        is_corrected = line.startswith("skorygowana rcem")
        if not (is_original or is_corrected):
            continue

        candidate = " ".join(lines[index - 1 : index + 4])
        price_match = PRICE_RE.search(candidate)
        if not price_match:
            continue

        price = _parse_decimal(price_match.group(1))
        if price is None:
            continue

        month_key = f"{current_year:04d}-{current_month_number:02d}"
        prices[month_key] = RCEmPrice(
            month=month_key,
            price_pln_mwh=price,
            publication_date=_parse_publication_date(candidate),
            corrected=is_corrected,
            source=source,
        )

    return prices


async def async_fetch_rcem_prices(
    session: "ClientSession",
    url: str = PSE_RCEM_URL,
) -> dict[str, RCEmPrice]:
    """Fetch and parse RCEm prices from PSE."""

    async with session.get(url, timeout=30) as response:
        response.raise_for_status()
        html = await response.text()
    return parse_rcem_html(html, source=url)
