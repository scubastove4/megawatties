"""Fetch final-energy CSVs into data/landing. HTTP 404 means the file is not published yet."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import urllib.error
import urllib.request

from log import get_logger
from capture.manifest import Manifest, store_bytes
from shared.filenames import PriceFile, fallback_daily_requests, initial_price_requests, select_price_files

logger = get_logger(__name__)

Fetcher = Callable[[str], bytes | None]


@dataclass
class DownloadReport:
    downloaded: list[str] = field(default_factory=list)
    replaced: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def urllib_fetcher(url: str) -> bytes | None:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def download_prices(
    *,
    start: date,
    end: date,
    today: date,
    now: datetime,
    landing: Path,
    manifest: Manifest,
    fetcher: Fetcher = urllib_fetcher,
) -> DownloadReport:
    logger.info("download start=%s end=%s today=%s", start.isoformat(), end.isoformat(), today.isoformat())
    report = DownloadReport()
    found: dict[str, bytes] = {}
    first_wave = initial_price_requests(start, end, today)
    _fetch_all(first_wave, fetcher, found, report)
    found_names = set(found)
    second_wave = [
        item
        for item in fallback_daily_requests(start, end, today, found_names)
        if item.name not in found
    ]
    _fetch_all(second_wave, fetcher, found, report)
    kept = set(select_price_files(list(found)))
    for name, content in found.items():
        if name not in kept:
            logger.info("skipped name=%s reason=completed_monthly_file", name)
            continue
        price_file = _price_file_for(name, first_wave + second_wave)
        outcome = store_bytes(
            manifest,
            relative_path=price_file.relative_path,
            content=content,
            url=price_file.url,
            status=price_file.status,
            trading_date=price_file.trading_date.isoformat() if price_file.trading_date else None,
            now=now,
            destination=landing / price_file.relative_path,
        )
        getattr(report, outcome).append(price_file.relative_path)
    logger.info(
        "download finished downloaded=%s replaced=%s unchanged=%s missing=%s",
        len(report.downloaded),
        len(report.replaced),
        len(report.unchanged),
        len(report.missing),
    )
    return report


def _fetch_all(
    requests: list[PriceFile],
    fetcher: Fetcher,
    found: dict[str, bytes],
    report: DownloadReport,
) -> None:
    for item in requests:
        if item.name in found:
            continue
        body = fetcher(item.url)
        if body is None:
            report.missing.append(item.name)
            logger.info("missing name=%s url=%s", item.name, item.url)
            continue
        found[item.name] = body


def _price_file_for(name: str, requests: list[PriceFile]) -> PriceFile:
    for item in requests:
        if item.name == name:
            return item
    raise KeyError(name)
