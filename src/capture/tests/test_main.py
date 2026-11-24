from datetime import date, datetime
from pathlib import Path
from urllib.error import URLError

import pytest

from capture.__main__ import main
from shared.calendar import AUCKLAND

NOW = datetime(2026, 11, 20, 9, 30, tzinfo=AUCKLAND)


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


def test_download_rejects_a_start_without_an_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("capture.__main__.datetime", type("Clock", (), {"now": staticmethod(lambda tz=None: NOW)}))
    with pytest.raises(SystemExit, match="end is required when start is provided"):
        main(["download", "--start", "2026-11-01"])
    written = tmp_path / "logs/capture/20261120T093000.log"
    assert written.is_file()
    text = written.read_text(encoding="utf-8")
    assert "download rejected reason=end is required when start is provided." in text
    assert "Optionally, omit both to use the current seven-day window." in text


def test_download_failure_is_written_to_the_run_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("capture.__main__.datetime", type("Clock", (), {"now": staticmethod(lambda tz=None: NOW)}))

    def fail(**kwargs: object) -> None:
        raise URLError("handshake timed out")

    monkeypatch.setattr("capture.__main__.download_prices", fail)
    with pytest.raises(SystemExit) as exc:
        main(["download", "--today", "2026-11-20"])
    assert exc.value.code == 1
    text = (tmp_path / "logs/capture/20261120T093000.log").read_text(encoding="utf-8")
    assert "download failed" in text
    assert "urlopen error handshake timed out" in text
