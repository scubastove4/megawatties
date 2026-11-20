# shared

Pure domain rules imported by capture and ingestion. These functions do not read the clock, the network, or the disk. Callers pass the bytes and the time.

## `__init__.py`

Marks `shared` as the package of those rules. It has no functions.

## `filenames.py`

Decides which final-energy files to ask for, and which of the ones that came back to keep.

A daily name is `YYYYMMDD_FinalEnergyPrices.csv`. The interim for that day is the same name with `_I` before `.csv`. A monthly name is `YYYYMM_FinalEnergyPrices.csv`, and the partial monthly rollup ends in `_incomplete`. Daily files land under `data/landing/daily/YYYY-MM-DD/`. Monthly files land under `data/landing/monthly/YYYY-MM/`. The public URL is the Electricity Authority blob under `FinalEnergyPrices`.

For a date in the current year, `initial_price_requests` asks for that day's final and its `_I` interim. For a past year it asks once per month for the `ByMonth` file and the `_incomplete` file. `fallback_daily_requests` asks for the daily final and interim only when that month's completed file was not in the set that came back. `select_price_files` drops daily files in a month that has a completed monthly file. An `_incomplete` monthly file does not cover those days, and both the interim and the final for the same day are kept.

`parse_price_filename` reads the status off the name: `_I` is interim, `_incomplete` is incomplete, and a name with neither is final.

## `calendar.py`

NZ business-day deadlines. Pass `now` in. A naive datetime is rejected.

The final for a trading date is due at 15:30 Pacific/Auckland on the next business day. Weekends and New Zealand public holidays are skipped, so a Friday trading date is due at 15:30 on Monday. `final_energy_due` is true once that moment has been reached.

`trading_period_window` is the seven calendar days ending on the date it is given, inclusive. A poll on 20 November asks for 14 November through 20 November.

Dispatch stays open until 09:30 Pacific/Auckland on trading-date + 3 calendar days. `dispatch_checksum_settled` is true only after that morning, with at least two observations, the last two checksums equal, and the latest observation at or after that morning. A changed checksum on the later poll keeps the file open.

## `checksums.py`

`sha256_hex` returns the hex digest of the bytes it is given. The manifest calls this before deciding whether a file is unchanged.

## `ranks.py`

Status comes from the filename. Interim ranks 1, incomplete ranks 2, and final ranks 3. An unknown status raises `ValueError`. These ranks are not used to pick a current price yet. That view comes in a later phase.

## `tests/test_filenames.py`

A completed monthly file suppresses that month's daily files. An `_incomplete` file does not. The interim and the final for one day are both kept. A past year asks for monthly files and falls back to daily files. The current year asks for the daily interim and final.

## `tests/test_calendar.py`

The window for 20 November 2026 is 14 November through 20 November. The Friday 13 November 2026 final is not due at 15:29 on Monday 16 November, and is due at 15:30. Dispatch for 10 November 2026 stays open on 12 November. It settles on 13 November once a later poll repeats the checksum, and stays open when that later checksum differs.
