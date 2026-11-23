from datetime import date, datetime

import pytest

from shared.calendar import (
    AUCKLAND,
    dispatch_checksum_settled,
    dispatch_window_open,
    final_energy_due,
    resolve_price_range,
    trading_period_window,
)


def test_trading_period_window_is_seven_days_ending_today() -> None:
    start, end = trading_period_window(date(2026, 11, 20))
    assert start == date(2026, 11, 14)
    assert end == date(2026, 11, 20)


def test_missing_dates_use_the_seven_day_window() -> None:
    assert resolve_price_range(None, None, date(2026, 11, 20)) == (
        date(2026, 11, 14),
        date(2026, 11, 20),
    )


def test_explicit_dates_keep_that_range() -> None:
    assert resolve_price_range(date(2026, 11, 1), date(2026, 11, 3), date(2026, 11, 20)) == (
        date(2026, 11, 1),
        date(2026, 11, 3),
    )


def test_one_end_of_the_range_is_rejected() -> None:
    with pytest.raises(ValueError, match="passed together"):
        resolve_price_range(date(2026, 11, 1), None, date(2026, 11, 20))


def test_friday_final_is_due_monday_at_1530() -> None:
    friday = date(2026, 11, 13)
    before = datetime(2026, 11, 16, 15, 29, tzinfo=AUCKLAND)
    at_deadline = datetime(2026, 11, 16, 15, 30, tzinfo=AUCKLAND)
    assert final_energy_due(friday, before) is False
    assert final_energy_due(friday, at_deadline) is True


def test_dispatch_stays_open_inside_the_three_day_window() -> None:
    trading = date(2026, 11, 10)
    inside = datetime(2026, 11, 12, 18, 30, tzinfo=AUCKLAND)
    assert dispatch_window_open(trading, inside) is True
    assert dispatch_checksum_settled(trading, inside, []) is False


def test_dispatch_settles_after_day_three_morning_when_the_checksum_repeats() -> None:
    trading = date(2026, 11, 10)
    first = datetime(2026, 11, 13, 9, 30, tzinfo=AUCKLAND)
    later = datetime(2026, 11, 13, 15, 30, tzinfo=AUCKLAND)
    observations = [(first, "abc"), (later, "abc")]
    assert dispatch_checksum_settled(trading, later, observations) is True
    changed = [(first, "abc"), (later, "def")]
    assert dispatch_checksum_settled(trading, later, changed) is False
