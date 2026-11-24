"""Download final-energy files onto the laptop.

    python -m capture download
    python -m capture download --start 2026-11-11 --end 2026-11-17
"""

import argparse
from datetime import date, datetime
from pathlib import Path

from capture.download import download_prices, urllib_fetcher
from log import get_logger, prepare_run_log, record_failure
from shared.calendar import AUCKLAND, resolve_price_range

logger = get_logger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="capture")
    subparsers = parser.add_subparsers(dest="command", required=True)
    download = subparsers.add_parser("download")
    download.add_argument("--start", type=date.fromisoformat)
    download.add_argument("--end", type=date.fromisoformat)
    download.add_argument("--today", type=date.fromisoformat)
    download.add_argument("--landing", type=Path, default=Path("data/landing"))
    download.add_argument("--log-config", type=Path)
    args = parser.parse_args(argv)
    if args.command == "download":
        now = datetime.now(AUCKLAND)
        _download(args, now)


def _download(args: argparse.Namespace, now: datetime) -> None:
    prepare_run_log(now, args.log_config)
    today = args.today or now.date()
    try:
        start, end = resolve_price_range(args.start, args.end, today)
    except ValueError as exc:
        logger.error("download rejected reason=%s", exc)
        raise SystemExit(str(exc)) from exc
    logger.info("download landing=%s start=%s end=%s", args.landing, start.isoformat(), end.isoformat())
    with record_failure(logger, "download failed"):
        download_prices(
            start=start,
            end=end,
            today=today,
            now=now,
            landing=args.landing,
            fetcher=urllib_fetcher,
        )


if __name__ == "__main__":
    main()
