from datetime import date

from shared.filenames import (
    fallback_daily_requests,
    initial_price_requests,
    parse_price_filename,
    select_price_files,
)
from shared.ranks import status_rank


def test_completed_monthly_file_suppresses_that_months_dailies() -> None:
    names = [
        "202510_FinalEnergyPrices.csv",
        "20251001_FinalEnergyPrices.csv",
        "20251001_FinalEnergyPrices_I.csv",
        "202511_FinalEnergyPrices_incomplete.csv",
        "20251101_FinalEnergyPrices.csv",
        "20251102_FinalEnergyPrices_I.csv",
    ]
    kept = select_price_files(names)
    assert "202510_FinalEnergyPrices.csv" in kept
    assert "20251001_FinalEnergyPrices.csv" not in kept
    assert "20251001_FinalEnergyPrices_I.csv" not in kept
    assert "202511_FinalEnergyPrices_incomplete.csv" in kept
    assert "20251101_FinalEnergyPrices.csv" in kept
    assert "20251102_FinalEnergyPrices_I.csv" in kept


def test_interim_and_final_for_the_same_day_are_both_kept() -> None:
    names = [
        "20261111_FinalEnergyPrices.csv",
        "20261111_FinalEnergyPrices_I.csv",
    ]
    assert select_price_files(names) == names


def test_status_rank_puts_incomplete_between_interim_and_final() -> None:
    assert status_rank("interim") == 1
    assert status_rank("incomplete") == 2
    assert status_rank("final") == 3
    assert parse_price_filename("20261112_FinalEnergyPrices_I.csv").status == "interim"
    assert parse_price_filename("202512_FinalEnergyPrices_incomplete.csv").status == "incomplete"


def test_past_year_requests_monthly_files_and_falls_back_to_dailies() -> None:
    start = date(2025, 10, 1)
    end = date(2025, 10, 2)
    today = date(2026, 11, 18)
    requested = initial_price_requests(start, end, today)
    initial = [item.name for item in requested]
    assert initial == [
        "202510_FinalEnergyPrices.csv",
        "202510_FinalEnergyPrices_incomplete.csv",
    ]
    assert requested[0].relative_path == "monthly/2025-10/202510_FinalEnergyPrices.csv"
    fallback = [item.name for item in fallback_daily_requests(start, end, today, found_names=set())]
    assert "20251001_FinalEnergyPrices.csv" in fallback
    assert "20251002_FinalEnergyPrices_I.csv" in fallback
    no_fallback = fallback_daily_requests(start, end, today, {"202510_FinalEnergyPrices.csv"})
    assert no_fallback == []


def test_current_year_requests_daily_interim_and_final_files() -> None:
    start = date(2026, 11, 11)
    end = date(2026, 11, 11)
    today = date(2026, 11, 18)
    requested = initial_price_requests(start, end, today)
    assert [item.name for item in requested] == [
        "20261111_FinalEnergyPrices.csv",
        "20261111_FinalEnergyPrices_I.csv",
    ]
    assert requested[0].relative_path == "daily/2026-11-11/20261111_FinalEnergyPrices.csv"
