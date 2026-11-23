"""One price poll. The clock is passed in. This module does not import Prefect."""

from datetime import datetime
from pathlib import Path

from capture.download import DownloadReport, Fetcher, download_prices, urllib_fetcher
from log import get_logger
from shared.calendar import AUCKLAND, trading_period_window

logger = get_logger(__name__)

POLL_CRON = "30 9,15,18 * * *"
POLL_TIMEZONE = "Pacific/Auckland"


def run_poll(
    *,
    now: datetime,
    landing: Path,
    fetcher: Fetcher = urllib_fetcher,
) -> DownloadReport:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    moment = now.astimezone(AUCKLAND)
    today = moment.date()
    start, end = trading_period_window(today)
    logger.info("poll start=%s end=%s today=%s", start.isoformat(), end.isoformat(), today.isoformat())
    return download_prices(
        start=start,
        end=end,
        today=today,
        now=moment,
        landing=landing,
        fetcher=fetcher,
    )
