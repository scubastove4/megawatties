"""Load logging.yaml and hand loggers to capture, orchestration, and ingestion."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from logging.config import dictConfig
from pathlib import Path
import logging
import re

import yaml

from shared.calendar import AUCKLAND

DEFAULT_CONFIG = Path(__file__).with_name("logging.yaml")
RUN_LOG_DIR = Path("logs/capture")
RUN_LOG_KEEP_DAYS = 7
_RUN_LOG_NAME = re.compile(r"^(?P<stamp>\d{8}T\d{6})\.log$")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def run_log_path(now: datetime) -> Path:
    moment = _auckland(now)
    return RUN_LOG_DIR / f"{moment.strftime('%Y%m%dT%H%M%S')}.log"


def cleanup_run_logs(
    directory: Path,
    now: datetime,
    keep_days: int = RUN_LOG_KEEP_DAYS,
) -> list[Path]:
    """Delete per-run logs strictly older than `keep_days`. Leave every other file."""
    cutoff = _auckland(now) - timedelta(days=keep_days)
    if not directory.is_dir():
        return []
    removed: list[Path] = []
    for path in directory.iterdir():
        match = _RUN_LOG_NAME.match(path.name)
        if match is None or not path.is_file():
            continue
        stamp = datetime.strptime(match.group("stamp"), "%Y%m%dT%H%M%S").replace(tzinfo=AUCKLAND)
        if stamp < cutoff:
            path.unlink()
            removed.append(path)
    return removed


def prepare_run_log(now: datetime, config: Path | None = None) -> None:
    """Drop expired run logs, then open the log for this run."""
    if config is None:
        cleanup_run_logs(RUN_LOG_DIR, now)
    configure_logging(config, now=now)


def configure_logging(path: Path | None = None, *, now: datetime | None = None) -> None:
    config_path = DEFAULT_CONFIG if path is None else path
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"logging config must be a mapping: {config_path}")
    if path is None:
        destination = run_log_path(_require_now(now))
        replaced = False
        for handler in payload.get("handlers", {}).values():
            if isinstance(handler, dict) and "filename" in handler:
                handler["filename"] = str(destination)
                replaced = True
        if not replaced:
            raise ValueError(f"logging config has no file handler: {config_path}")
    for handler in payload.get("handlers", {}).values():
        if not isinstance(handler, dict):
            continue
        filename = handler.get("filename")
        if isinstance(filename, str) and filename:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
    dictConfig(payload)


@contextmanager
def record_failure(logger: logging.Logger, message: str) -> Iterator[None]:
    """Write an unexpected failure and its traceback to the run log, then exit."""
    try:
        yield
    except Exception:
        logger.exception(message)
        raise SystemExit(1) from None


def _require_now(now: datetime | None) -> datetime:
    if now is None:
        raise ValueError("now must be timezone-aware")
    return now


def _auckland(now: datetime) -> datetime:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now.astimezone(AUCKLAND)
