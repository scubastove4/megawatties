"""NZ business-day deadlines. Pass `now` in; these functions do not read the clock."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import holidays

AUCKLAND = ZoneInfo("Pacific/Auckland")
FINAL_DUE_TIME = time(15, 30)
DISPATCH_SETTLE_DAYS = 3
DISPATCH_MORNING = time(9, 30)
TRADING_PERIOD_LOOKBACK_DAYS = 7


def trading_period_window(today: date) -> tuple[date, date]:
    """Seven calendar days ending on today, inclusive."""
    start = today - timedelta(days=TRADING_PERIOD_LOOKBACK_DAYS - 1)
    return start, today


def _nz_holidays() -> holidays.HolidayBase:
    return holidays.country_holidays("NZ")


def is_business_day(day: date, nz_holidays: holidays.HolidayBase | None = None) -> bool:
    holidays_nz = _nz_holidays() if nz_holidays is None else nz_holidays
    return day.weekday() < 5 and day not in holidays_nz


def next_business_day(day: date, nz_holidays: holidays.HolidayBase | None = None) -> date:
    holidays_nz = _nz_holidays() if nz_holidays is None else nz_holidays
    candidate = day + timedelta(days=1)
    while not is_business_day(candidate, holidays_nz):
        candidate += timedelta(days=1)
    return candidate


def _aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return moment.astimezone(AUCKLAND)


def final_due_at(trading_date: date) -> datetime:
    due_day = next_business_day(trading_date)
    return datetime.combine(due_day, FINAL_DUE_TIME, tzinfo=AUCKLAND)


def final_energy_due(trading_date: date, now: datetime) -> bool:
    return _aware(now) >= final_due_at(trading_date)


def dispatch_settled_at(trading_date: date) -> datetime:
    settled_day = trading_date + timedelta(days=DISPATCH_SETTLE_DAYS)
    return datetime.combine(settled_day, DISPATCH_MORNING, tzinfo=AUCKLAND)


def dispatch_window_open(trading_date: date, now: datetime) -> bool:
    return _aware(now) < dispatch_settled_at(trading_date)


def dispatch_checksum_settled(
    trading_date: date,
    now: datetime,
    observations: list[tuple[datetime, str]],
) -> bool:
    """True once day-three morning has passed and a later poll saw the same checksum."""
    if dispatch_window_open(trading_date, now):
        return False
    stamped = [(_aware(moment), digest) for moment, digest in observations]
    stamped.sort(key=lambda item: item[0])
    if len(stamped) < 2:
        return False
    previous_digest = stamped[-2][1]
    latest_moment, latest_digest = stamped[-1]
    if latest_digest != previous_digest:
        return False
    return latest_moment >= dispatch_settled_at(trading_date)
