"""Run one price poll, or serve the Auckland schedule.

    python -m orchestration poll
    python -m orchestration serve
"""

import argparse
from datetime import datetime
from pathlib import Path

from log import get_logger, prepare_run_log, record_failure
from orchestration.poll import run_poll
from shared.calendar import AUCKLAND

logger = get_logger("orchestration.poll")

POLL_CRON = "30 9,15,18 * * *"
POLL_TIMEZONE = "Pacific/Auckland"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="orchestration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    poll = subparsers.add_parser("poll")
    poll.add_argument("--landing", type=Path, default=Path("data/landing"))
    poll.add_argument("--log-config", type=Path)
    subparsers.add_parser("serve")
    args = parser.parse_args(argv)
    if args.command == "poll":
        now = datetime.now(AUCKLAND)
        prepare_run_log(now, args.log_config)
        with record_failure(logger, "poll failed"):
            run_poll(now=now, landing=args.landing)
        return
    _serve()


def _serve(cron: str = POLL_CRON, timezone: str = POLL_TIMEZONE) -> None:
    try:
        from orchestration.flow import serve_poll
    except ModuleNotFoundError as exc:
        if exc.name != "prefect":
            raise
        raise SystemExit("Install the orchestration extra: pip install -e '.[orchestration]'") from exc
    serve_poll(cron=cron, timezone=timezone)


if __name__ == "__main__":
    main()
