# capture

Download EMI final-energy CSVs onto the laptop. The download command fetches files and updates the manifest. It does not delete anything.

## `__init__.py`

Marks `capture` as the package that downloads final-energy CSVs. It has no functions.

## `__main__.py`

The command line. `python -m capture download --start … --end …` loads `src/log/logging.yaml`, calls `download_prices`, and leaves each trading date or month with its own `manifest.json` under `data/landing`.

`--today` defaults to the laptop's current date and decides whether a date is asked for as a daily file or a `ByMonth` file. `--landing` is `data/landing`. `--log-config` points at a different logging file when you pass one. The clock read for the manifest observation lives here, in Auckland time, and is passed into the download.

## `download.py`

Fetches the files `shared` asked for and hands the bytes to `store_bytes`.

`urllib_fetcher` treats HTTP 404 as "not published yet" and returns no bytes. Any other HTTP error is raised. Tests pass their own fetcher, so a unit test does not call EMI.

`download_prices` asks for the first wave, then a fallback wave of daily files for a past month whose completed monthly file was missing. It drops a daily file when `select_price_files` says a completed monthly file already covers that month, and logs that skip. Every other found file is stored. Files for one trading date share `daily/YYYY-MM-DD/manifest.json`. Files for one month share `monthly/YYYY-MM/manifest.json`. The report lists each path as `downloaded`, `replaced`, `unchanged`, or `missing`.

## `manifest.py`

The checksum gate. One JSON file per trading-date folder or month folder, not one file for all of `data/landing`.

`FileRecord` is one captured file: relative path, sha256, byte size, source URL, status, trading date, whether it has been uploaded, whether the local CSV is still on disk, and the list of times that hash was seen.

`Manifest.load` returns an empty manifest when that folder's file is not there yet. `Manifest.save` writes to a temporary file and then replaces the real one, so a failed write does not leave a half-written manifest. A run that stops midway leaves the dates it already saved, and the next run finishes the rest.

`store_bytes` hashes the new bytes. The same hash is not written again. The observation list still records that this poll saw it, and `local_exists` follows whether the CSV is on disk. A new hash replaces the local CSV, clears `uploaded` back to false, and returns `replaced`. The first time a path is seen, it returns `downloaded`.

## `cleanup.py`

Deletes local CSVs only after they have been uploaded and the trading date is closed. The download command does not call this. A later upload step marks files uploaded, and orchestration calls `delete_closed_files` on a schedule.

It reads `data/landing/daily/YYYY-MM-DD/manifest.json` and removes the CSVs in that folder together. The manifest stays, with `local_exists` set to false, so a later poll still knows the checksum. The files stay when the daily final is not uploaded (`final_not_uploaded`), when no dispatch file is tracked yet (`dispatch_not_tracked`), when dispatch is not uploaded (`dispatch_not_uploaded`), or when the dispatch checksum is still open (`dispatch_checksum_open`). Phase 1 has no dispatch download, so a real run leaves the CSVs in `data/landing`. Monthly folders are left alone.

## `tests/test_download.py`

An unchanged checksum is not written again. A changed checksum replaces the local file and clears `uploaded`.

## `tests/test_cleanup.py`

Local files stay through the open dispatch window, stay when dispatch is not tracked, and stay when the final has not been uploaded. They are removed once the final is uploaded and the dispatch checksum has settled. The trading-date `manifest.json` remains after the CSVs are gone.
