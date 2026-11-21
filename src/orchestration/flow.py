"""The scheduled Prefect flow. Import this module only when Prefect is installed."""

from datetime import datetime
from pathlib import Path

from prefect import flow
from prefect.schedules import Cron

from log import prepare_run_log
from orchestration.poll import POLL_CRON, POLL_TIMEZONE, run_poll
from shared.calendar import AUCKLAND


@flow(name="poll-prices")
def poll_prices(landing: str = "data/landing") -> None:
    now = datetime.now(AUCKLAND)
    prepare_run_log(now)
    run_poll(now=now, landing=Path(landing))


def serve_poll() -> None:
    poll_prices.serve(
        name="poll-prices",
        schedule=Cron(POLL_CRON, timezone=POLL_TIMEZONE, slug="auckland-price-polls"),
    )
