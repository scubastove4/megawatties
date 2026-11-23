# Megawatties

A download run starts at `python -m capture download`. With no dates, it fetches the seven calendar days ending on the Auckland date. `--start` and `--end` select a different range, and they are passed together. The command loads `src/log/logging.yaml`, writes `logs/capture/YYYYMMDDTHHMMSS.log` for that run, fetches the files, and writes one `manifest.json` in each trading-date or month folder under `data/landing`. It does not delete downloaded CSVs. A run deletes per-run logs strictly older than seven days.

A scheduled poll is `python -m orchestration poll`, after `pip install -e ".[orchestration]"`. It downloads the seven calendar days ending on the Auckland date. `python -m orchestration serve` runs that poll at 9:30, 15:30, and 18:30 Pacific/Auckland. The poll does not delete anything.

`src/orchestration/com.megawatties.poll.plist` runs that same poll from macOS without leaving a terminal open. The three paths inside it are this checkout, `.venv/bin/python`, and the `logs/poll.out.log` and `logs/poll.err.log` files. Change those paths if the repo moves. Prior to copying the file to `~/Library/LaunchAgents/com.megawatties.poll.plist`, change `<path to projects folder>` to where you keep `megawatties`. **NOTE:** Editing the copy in the repo does not change the loaded agent. Copy it again after a change, then load it:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.megawatties.poll.plist
```

This runs one poll immediately:

```bash
launchctl kickstart -p gui/$(id -u)/com.megawatties.poll
```

This unloads the agent. The plist and the log files stay on disk:

```bash
launchctl bootout gui/$(id -u)/com.megawatties.poll
```

The `Hour` values are read by UserEventAgent. The poll, once started, still names its log with the Auckland clock. On this Mac the agent clock is US Eastern, and Auckland daylight time is 18 hours ahead of Eastern standard time, so a plist hour shows up six hours earlier on the Auckland clock the next morning. The polls are meant to run at 9:30, 15:30, and 18:30 Auckland. With this agent clock those are plist hours 15:30, 21:30, and 0:30, as seen in the checked in file. After a daylight-saving change on either clock, compare a timestamp in `logs/capture/` with the plist hour and shift the hours by that same gap.

`shared` decides which files to ask for. For a date in the current year it asks for that day's final and its `_I` interim. For a past year it asks for the `ByMonth` file and the `_incomplete` file. If the completed monthly file comes back as HTTP 404, it falls back to the daily files for that month. A 404 is "not published yet," so the run records the name as missing and continues. A completed monthly file covers that month, so those daily files are not saved. An `_incomplete` monthly file does not cover them, and both the interim and the final for the same day are kept.
