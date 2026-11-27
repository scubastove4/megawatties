"""Download final-energy files onto the laptop.

    python -m capture download
    python -m capture download --start 2026-11-11 --end 2026-11-17
"""

import argparse
from datetime import date, datetime
from pathlib import Path

from capture.download import download_prices, urllib_fetcher
from capture.upload import upload_prices
from log import get_logger, prepare_run_log, record_failure
from shared.calendar import AUCKLAND, resolve_price_range

logger = get_logger(__name__)


def main(argv: list[str] | None = None) -> None:
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument("--start", type=date.fromisoformat)
    options.add_argument("--end", type=date.fromisoformat)
    options.add_argument("--today", type=date.fromisoformat)
    options.add_argument("--landing", type=Path, default=Path("data/landing"))
    options.add_argument("--log-config", type=Path)

    parser = argparse.ArgumentParser(prog="capture")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("download", parents=[options])
    subparsers.add_parser("upload", parents=[options])
    subparsers.add_parser("download/upload", parents=[options])

    args = parser.parse_args(argv)

    now = datetime.now(AUCKLAND)
    start, end, today = prepare_run(now, args)

    if args.command == "download":
        _download(args.landing, now, start, end, today)

    elif args.command == "upload":
        _upload(args.landing, now, start, end, today)

    elif args.command == "download/upload":
        download_failed = False
        upload_failed = False

        try:
            _download(args.landing, now, start, end, today)
        except SystemExit:
            download_failed = True

        try:
            _upload(args.landing, now, start, end, today)
        except SystemExit:
            upload_failed = True

        if download_failed or upload_failed:
            logger.error(
                "command=download/upload finished download_failed=%s upload_failed=%s",
                download_failed,
                upload_failed,
            )
            raise SystemExit(1)



def prepare_run(now: datetime, args: argparse.Namespace) -> tuple[date, date, date]:

    prepare_run_log(now, args.log_config)
    today = args.today or now.date()

    try:
        start, end = resolve_price_range(args.start, args.end, today)
    except ValueError as exc:
        logger.error("command=%s rejected reason=%s", args.command, exc)
        raise SystemExit(str(exc)) from exc
    logger.info("command=%s start=%s end=%s", args.command, start.isoformat(), end.isoformat())

    return start, end, today


def _download(landing: Path, now: datetime, start: date, end: date, today: date) -> None:
    with record_failure(logger, "download failed"):
        download_prices(
            start=start,
            end=end,
            today=today,
            now=now,
            landing=landing,
            fetcher=urllib_fetcher,
        )

def _upload(landing: Path, now: datetime, start: date, end: date, today: date) -> None:
    with record_failure(logger, "upload failed"):
        upload_prices(
            start=start,
            end=end,
            today=today,
            now=now,
            landing=landing
        )


if __name__ == "__main__":
    main()
