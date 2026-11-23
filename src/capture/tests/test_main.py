from datetime import date

import pytest

from capture.__main__ import main


def test_download_without_dates_uses_the_seven_day_window(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr("capture.__main__.prepare_run_log", lambda *args, **kwargs: None)

    def fake_download(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("capture.__main__.download_prices", fake_download)
    main(["download", "--today", "2026-11-20", "--landing", "unused"])
    assert captured["start"] == date(2026, 11, 14)
    assert captured["end"] == date(2026, 11, 20)
    assert captured["today"] == date(2026, 11, 20)


def test_download_with_dates_keeps_that_range(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr("capture.__main__.prepare_run_log", lambda *args, **kwargs: None)

    def fake_download(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("capture.__main__.download_prices", fake_download)
    main(
        [
            "download",
            "--start",
            "2026-11-01",
            "--end",
            "2026-11-03",
            "--today",
            "2026-11-20",
        ]
    )
    assert captured["start"] == date(2026, 11, 1)
    assert captured["end"] == date(2026, 11, 3)


def test_download_rejects_a_start_without_an_end() -> None:
    with pytest.raises(SystemExit, match="passed together"):
        main(["download", "--start", "2026-11-01"])
