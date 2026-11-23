# orchestration

Prefect polls on the laptop. A poll calls capture and leaves the local files in place. It does not upload to the volume and it does not delete CSVs.

Install Prefect with the laptop extra: `pip install -e ".[orchestration]"`. Databricks does not install that extra. The bundle excludes this package.

## `__init__.py`

Marks `orchestration` as the package that schedules capture. It has no functions.

## `poll.py`

`run_poll` takes an aware `now`, converts it to Pacific/Auckland, and downloads the seven calendar days ending on that date. The caller passes the clock. A naive datetime is rejected. The default fetcher is the capture HTTP fetcher. Tests pass their own fetcher, so a unit test does not call EMI.

`POLL_CRON` is `30 9,15,18 * * *` and `POLL_TIMEZONE` is `Pacific/Auckland`. Those are the 9:30, 15:30, and 18:30 polls.

## `flow.py`

The Prefect flow `poll-prices`. It reads the Auckland clock, then calls `run_poll` for `data/landing`. `serve_poll` serves that flow on the cron above. This module imports Prefect, so it is loaded only when the extra is installed.

## `__main__.py`

`python -m orchestration poll` runs one poll now. It deletes per-run logs strictly older than seven days, then writes `logs/capture/YYYYMMDDTHHMMSS.log` for this run. `python -m orchestration serve` starts the schedule, and each scheduled run does that same log cleanup before the download. `--landing` changes the folder for one poll. `--log-config` points at a different logging file for one poll.

## `tests/test_poll.py`

The cron is the three Auckland times. A poll at 09:30 on 20 November 2026 asks for 14 November through 20 November and does not ask for 13 November. Nothing is written when every response is empty. A naive clock is rejected.
