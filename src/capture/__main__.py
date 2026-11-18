"""Download final-energy files onto the laptop.

    python -m capture download --start 2026-11-11 --end 2026-11-17
"""

import argparse
from datetime import date, datetime
from pathlib import Path

from capture.download import download_prices, urllib_fetcher
from log import configure_logging, get_logger
from capture.manifest import Manifest
from shared.calendar import AUCKLAND

logger = get_logger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="capture")
    subparsers = parser.add_subparsers(dest="command", required=True)
    download = subparsers.add_parser("download")
    download.add_argument("--start", required=True, type=date.fromisoformat)
    download.add_argument("--end", required=True, type=date.fromisoformat)
    download.add_argument("--today", type=date.fromisoformat)
    download.add_argument("--landing", type=Path, default=Path("data/landing"))
    download.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    download.add_argument("--log-config", type=Path)
    args = parser.parse_args(argv)
    configure_logging(args.log_config)
    if args.command == "download":
        _download(args)


def _download(args: argparse.Namespace) -> None:
    today = args.today or date.today()
    now = datetime.now(AUCKLAND)
    logger.info(
        "download landing=%s manifest=%s",
        args.landing,
        args.manifest,
    )
    manifest = Manifest.load(args.manifest)
    download_prices(
        start=args.start,
        end=args.end,
        today=today,
        now=now,
        landing=args.landing,
        manifest=manifest,
        fetcher=urllib_fetcher,
    )
    manifest.save(args.manifest)
    logger.info("wrote manifest path=%s files=%s", args.manifest, len(manifest.files))


if __name__ == "__main__":
    main()
