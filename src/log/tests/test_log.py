from datetime import datetime
from pathlib import Path
from urllib.error import URLError
import logging

import pytest

from log import configure_logging, get_logger, prepare_run_log, record_failure
from log.log import DEFAULT_CONFIG, cleanup_run_logs, run_log_path
from shared.calendar import AUCKLAND

NOW = datetime(2026, 11, 21, 9, 30, tzinfo=AUCKLAND)


def test_packaged_yaml_sets_the_root_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    configure_logging(now=NOW)
    assert DEFAULT_CONFIG.is_file()
    assert logging.getLogger().level == logging.INFO
    assert (tmp_path / "logs/capture/20261121T093000.log").is_file()


def test_configure_logging_reads_an_override_file(tmp_path: Path) -> None:
    path = tmp_path / "logging.yaml"
    path.write_text(
        "\n".join(
            [
                "version: 1",
                "disable_existing_loggers: false",
                "root:",
                "  level: ERROR",
                "  handlers: []",
            ]
        ),
        encoding="utf-8",
    )
    configure_logging(path)
    assert logging.getLogger().level == logging.ERROR


def test_prepare_run_log_deletes_files_older_than_seven_days(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / "logs/capture"
    directory.mkdir(parents=True)
    expired = directory / "20261114T092959.log"
    boundary = directory / "20261114T093000.log"
    recent = directory / "20261120T180000.log"
    other = directory / "notes.txt"
    for path in (expired, boundary, recent, other):
        path.write_text("line\n", encoding="utf-8")

    removed = cleanup_run_logs(directory, NOW)

    assert removed == [expired]
    assert expired.exists() is False
    assert boundary.exists() is True
    assert recent.exists() is True
    assert other.exists() is True
    prepare_run_log(NOW)
    assert (directory / "20261121T093000.log").is_file()


def test_record_failure_writes_the_traceback_to_the_run_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    configure_logging(now=NOW)
    with pytest.raises(SystemExit) as exc:
        with record_failure(get_logger("capture.download"), "download failed"):
            raise URLError("handshake timed out")
    assert exc.value.code == 1
    text = (tmp_path / "logs/capture/20261121T093000.log").read_text(encoding="utf-8")
    assert "ERROR capture.download download failed" in text
    assert "urlopen error handshake timed out" in text


def test_run_log_path_rejects_a_naive_clock() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        run_log_path(datetime(2026, 11, 21, 9, 30))
