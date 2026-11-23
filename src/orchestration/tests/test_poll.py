from datetime import datetime
from pathlib import Path

import pytest

from orchestration.poll import POLL_CRON, POLL_TIMEZONE, run_poll
from shared.calendar import AUCKLAND


def test_polls_are_the_three_auckland_times() -> None:
    assert POLL_CRON == "30 9,15,18 * * *"
    assert POLL_TIMEZONE == "Pacific/Auckland"


def test_poll_asks_for_seven_calendar_days_ending_today(tmp_path: Path) -> None:
    seen: list[str] = []

    def fetcher(url: str) -> None:
        seen.append(url.rsplit("/", 1)[-1])
        return None

    now = datetime(2026, 11, 20, 9, 30, tzinfo=AUCKLAND)
    report = run_poll(now=now, landing=tmp_path, fetcher=fetcher)
    assert "20261114_FinalEnergyPrices.csv" in seen
    assert "20261120_FinalEnergyPrices_I.csv" in seen
    assert "20261120_FinalEnergyPrices.csv" in seen
    assert "20261113_FinalEnergyPrices.csv" not in seen
    assert report.downloaded == []
    assert report.replaced == []
    assert list(tmp_path.rglob("*.csv")) == []


def test_poll_rejects_a_naive_clock() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        run_poll(now=datetime(2026, 11, 20, 9, 30), landing=Path("data/landing"))
