# Megawatties

A download run starts at `python -m capture download --start … --end …`. The command loads `src/log/logging.yaml`, fetches the files, and writes one `manifest.json` in each trading-date or month folder under `data/landing`. It does not delete anything.

A scheduled poll is `python -m orchestration poll`, after `pip install -e ".[orchestration]"`. It downloads the seven calendar days ending on the Auckland date. `python -m orchestration serve` runs that poll at 9:30, 15:30, and 18:30 Pacific/Auckland. The poll does not delete anything.

`shared` decides which files to ask for. For a date in the current year it asks for that day's final and its `_I` interim. For a past year it asks for the `ByMonth` file and the `_incomplete` file. If the completed monthly file comes back as HTTP 404, it falls back to the daily files for that month. A 404 is "not published yet," so the run records the name as missing and continues. A completed monthly file covers that month, so those daily files are not saved. An `_incomplete` monthly file does not cover them, and both the interim and the final for the same day are kept.
