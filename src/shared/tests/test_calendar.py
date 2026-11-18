from datetime import date, datetime

from shared.calendar import AUCKLAND, dispatch_checksum_settled, dispatch_window_open, final_energy_due


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
