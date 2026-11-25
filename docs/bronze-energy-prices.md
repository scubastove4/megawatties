# Bronze energy prices

Create `workspace.emi.bronze_energy_price` and load the one final already in the volume. This does not upload other dates, create a job, redeploy the bundle, or delete local files.

The catalog is `workspace`. The schema is `emi`. The volume is `workspace.emi.landing`. Use the serverless SQL warehouse that is already there. Do not create a warehouse.

The file is `daily/2026-11-10/20261110_FinalEnergyPrices.csv`. Its header is `TradingDate,TradingPeriod,PointOfConnection,DollarsPerMegawattHour`. The local copy has 11808 data rows and sha256 `3e12a850b7f53f912018560f14eac64fcea86bed54854c04eb8e2a611ffd819b`. This copy has no EMI modified time, so `file_modified_at` stays null. The file status is `final`.

Bronze keeps the four price columns as text, plus the file they came from. `ingested_files` is the checksum record. A later run of this script skips the file when that checksum is already stored.

## 1. Confirm the volume file

From the repo root:

```bash
databricks fs ls -l \
  dbfs:/Volumes/workspace/emi/landing/daily/2026-11-10 \
  --profile megawatties
```

The listed size should be 329269 bytes, the same as `data/landing/daily/2026-11-10/20261110_FinalEnergyPrices.csv`. If the volume file is missing, stop. Do not copy another date up.

## 2. Create the tables

In the SQL editor, attached to the existing serverless warehouse:

```sql
CREATE TABLE IF NOT EXISTS workspace.emi.bronze_energy_price (
  trading_date STRING,
  trading_period STRING,
  point_of_connection STRING,
  dollars_per_megawatt_hour STRING,
  source_file STRING,
  file_status STRING,
  file_modified_at TIMESTAMP,
  ingested_at TIMESTAMP,
  checksum STRING
)
USING DELTA;

CREATE TABLE IF NOT EXISTS workspace.emi.ingested_files (
  source_file STRING,
  checksum STRING,
  bytes BIGINT,
  ingested_at TIMESTAMP
)
USING DELTA;
```

In Catalog Explorer, `workspace` → `emi` should list `bronze_energy_price` and `ingested_files`. Both are empty. If either statement is rejected, stop.

## 3. Load the 10 November final

Run this once. The price columns stay text, so a value such as `19.90` is stored as `19.90`. The insert does nothing when this checksum is already in `ingested_files`.

```sql
INSERT INTO workspace.emi.bronze_energy_price
SELECT
  TradingDate,
  TradingPeriod,
  PointOfConnection,
  DollarsPerMegawattHour,
  'daily/2026-11-10/20261110_FinalEnergyPrices.csv',
  'final',
  CAST(NULL AS TIMESTAMP),
  current_timestamp(),
  '3e12a850b7f53f912018560f14eac64fcea86bed54854c04eb8e2a611ffd819b'
FROM read_files(
  '/Volumes/workspace/emi/landing/daily/2026-11-10/20261110_FinalEnergyPrices.csv',
  format => 'csv',
  header => true,
  schemaHints => 'TradingDate STRING, TradingPeriod STRING, PointOfConnection STRING, DollarsPerMegawattHour STRING'
)
WHERE NOT EXISTS (
  SELECT 1
  FROM workspace.emi.ingested_files
  WHERE checksum = '3e12a850b7f53f912018560f14eac64fcea86bed54854c04eb8e2a611ffd819b'
);
```

`ingested_at` is the warehouse clock at the moment of the insert.

## 4. Check the load before recording the checksum

```sql
SELECT COUNT(*) AS rows
FROM workspace.emi.bronze_energy_price;

SELECT trading_date, trading_period, point_of_connection, dollars_per_megawatt_hour
FROM workspace.emi.bronze_energy_price
WHERE point_of_connection = 'ABY0111'
  AND trading_period = '1';
```

Expect 11808 rows. The sample row is trading date `2026-11-10`, period `1`, node `ABY0111`, price `19.90`. If the count or the sample differs, stop. Do not run step 5, and do not run step 3 again.

## 5. Record the checksum

Run this only after step 4 matches. A second run does not add another row for this checksum.

```sql
INSERT INTO workspace.emi.ingested_files
SELECT
  'daily/2026-11-10/20261110_FinalEnergyPrices.csv',
  '3e12a850b7f53f912018560f14eac64fcea86bed54854c04eb8e2a611ffd819b',
  329269,
  current_timestamp()
WHERE NOT EXISTS (
  SELECT 1
  FROM workspace.emi.ingested_files
  WHERE checksum = '3e12a850b7f53f912018560f14eac64fcea86bed54854c04eb8e2a611ffd819b'
);
```

```sql
SELECT source_file, checksum, bytes
FROM workspace.emi.ingested_files;
```

Expect one row: that source path, that checksum, and 329269 bytes.

## 6. Stop

The bronze table holds the 10 November final, and `ingested_files` holds its checksum. This load was confirmed: 11808 rows are in `bronze_energy_price`, the checksum row is in `ingested_files`, and running the insert again added no rows. Leave every other date on the laptop. Do not create a Databricks job, redeploy the bundle, load another file, or build silver and gold.
