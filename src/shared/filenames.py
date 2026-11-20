"""Final-energy filenames and which of them to keep."""

from dataclasses import dataclass
from datetime import date, timedelta
import re

FINAL_ENERGY_BASE = (
    "https://emidatasets.blob.core.windows.net/publicdata/"
    "Datasets/Wholesale/DispatchAndPricing/FinalEnergyPrices"
)

_DAILY = re.compile(r"^(?P<ymd>\d{8})_FinalEnergyPrices(?P<interim>_I)?\.csv$")
_MONTHLY = re.compile(r"^(?P<ym>\d{6})_FinalEnergyPrices(?P<incomplete>_incomplete)?\.csv$")


@dataclass(frozen=True)
class PriceFile:
    name: str
    kind: str
    status: str
    month: str
    trading_date: date | None
    url: str

    @property
    def relative_path(self) -> str:
        if self.kind == "monthly":
            return f"monthly/{self.month[:4]}-{self.month[4:]}/{self.name}"
        if self.trading_date is None:
            raise ValueError(f"daily price file has no trading date: {self.name}")
        return f"daily/{self.trading_date.isoformat()}/{self.name}"


def parse_price_filename(name: str) -> PriceFile:
    daily = _DAILY.match(name)
    if daily:
        ymd = daily.group("ymd")
        trading_date = date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]))
        status = "interim" if daily.group("interim") else "final"
        return PriceFile(
            name=name,
            kind="daily",
            status=status,
            month=ymd[:6],
            trading_date=trading_date,
            url=f"{FINAL_ENERGY_BASE}/{name}",
        )
    monthly = _MONTHLY.match(name)
    if monthly:
        status = "incomplete" if monthly.group("incomplete") else "final"
        folder = f"{FINAL_ENERGY_BASE}/ByMonth/{name}"
        return PriceFile(
            name=name,
            kind="monthly",
            status=status,
            month=monthly.group("ym"),
            trading_date=None,
            url=folder,
        )
    raise ValueError(f"not a final-energy price filename: {name}")


def select_price_files(names: list[str]) -> list[str]:
    """A completed monthly file covers that month. An incomplete monthly file does not."""
    parsed = [parse_price_filename(name) for name in names]
    complete_months = {item.month for item in parsed if item.kind == "monthly" and item.status == "final"}
    return [item.name for item in parsed if not (item.kind == "daily" and item.month in complete_months)]


def _month_key(day: date) -> str:
    return f"{day.year}{day.month:02d}"


def _dates(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("end is before start")
    days = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def daily_price_files(day: date) -> list[PriceFile]:
    ymd = day.strftime("%Y%m%d")
    return [
        parse_price_filename(f"{ymd}_FinalEnergyPrices.csv"),
        parse_price_filename(f"{ymd}_FinalEnergyPrices_I.csv"),
    ]


def monthly_price_files(year: int, month: int) -> list[PriceFile]:
    ym = f"{year}{month:02d}"
    return [
        parse_price_filename(f"{ym}_FinalEnergyPrices.csv"),
        parse_price_filename(f"{ym}_FinalEnergyPrices_incomplete.csv"),
    ]


def initial_price_requests(start: date, end: date, today: date) -> list[PriceFile]:
    """ByMonth for completed years. Daily interim and final files for the current year."""
    requests: list[PriceFile] = []
    seen_months: set[str] = set()
    for day in _dates(start, end):
        if day.year < today.year:
            key = _month_key(day)
            if key not in seen_months:
                requests.extend(monthly_price_files(day.year, day.month))
                seen_months.add(key)
            continue
        requests.extend(daily_price_files(day))
    return requests


def fallback_daily_requests(start: date, end: date, today: date, found_names: set[str]) -> list[PriceFile]:
    """Daily files for a past month whose completed monthly file was not published."""
    requests: list[PriceFile] = []
    for day in _dates(start, end):
        if day.year >= today.year:
            continue
        complete = f"{_month_key(day)}_FinalEnergyPrices.csv"
        if complete in found_names:
            continue
        requests.extend(daily_price_files(day))
    return requests
