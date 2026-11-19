# Unity Catalog smoke upload

One local CSV is copied into a Unity Catalog volume. This does not create tables, upload the rest of the landing zone, or delete anything on the laptop.

The catalog name comes from the Free Edition workspace. The schema is `emi`. The volume is `emi.landing`. The bundle file `databricks.yml` is written after the catalog name is known. No service principal, no token in the repo, and no second SQL warehouse.

## 1. Create the Free Edition workspace

Sign up from [Databricks Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition). Choose Free Edition, not a trial and not the retired Community Edition.

When the workspace opens, copy the browser address. It looks like `https://dbc-xxxxxxxx-xxxx.cloud.databricks.com`. That host is what the CLI logs in to.

## 2. Find the catalog

In the workspace sidebar, open **Catalog**. The workspace catalog is listed there. On Free Edition it is often named the same as the workspace, not `main`.

Write that name down. Do not create another catalog.

Free Edition users can use that catalog and its `default` schema. The project uses a separate schema, `emi`. Creating it is step 5. If that statement is rejected, stop. Do not put the file in `default` until we decide to change the project layout.

## 3. Install the CLI

On this Mac, Homebrew is already installed:

```bash
brew tap databricks/tap
brew trust databricks/tap
xcode-select --install (run is xcode cli is not installed)
brew install databricks
databricks version
```

## 4. Log in from the laptop

Run this from any directory and substitute the workspace host:

```bash
databricks auth login --host https://dbc-xxxxxxxx-xxxx.cloud.databricks.com
```

Name the profile `megawatties` when asked. The browser login stores the token in the macOS Keychain. `~/.databrickscfg` keeps the host and profile name. Do not copy that file or the token into the repo.

Check the login:

```bash
databricks current-user me --profile megawatties
databricks catalogs list --profile megawatties
```

The catalog list should include the name from step 2.

## 5. Create the schema and volume

In the workspace, open the SQL editor and attach the serverless SQL warehouse that is already there. Do not create a warehouse.

Substitute the catalog name:

```sql
CREATE SCHEMA IF NOT EXISTS workspace.emi;
CREATE VOLUME IF NOT EXISTS workspace.emi.landing;
```

In Catalog Explorer, open `workspace` → `emi` → `landing`. The volume should be empty. Volumes are for files. This step does not create a table.

## 6. Copy one file

Use one final CSV already in `data/landing`. The volume path mirrors the laptop path. From the repo root, substitute the catalog name:

```bash
databricks fs mkdirs \
  dbfs:/Volumes/workspace/emi/landing/daily/2026-11-10 \
  --profile megawatties

databricks fs cp \
  data/landing/daily/2026-11-10/20261110_FinalEnergyPrices.csv \
  dbfs:/Volumes/workspace/emi/landing/daily/2026-11-10/20261110_FinalEnergyPrices.csv \
  --profile megawatties
```

The CLI needs the `dbfs:/Volumes` prefix. Free Edition does not use the DBFS root.

List the uploaded file and compare its size with the local file:

```bash
databricks fs ls -l \
  dbfs:/Volumes/workspace/emi/landing/daily/2026-11-10 \
  --profile megawatties
  
ls -l data/landing/daily/2026-11-10/20261110_FinalEnergyPrices.csv
```

Also open that file in Catalog Explorer. The two sizes should match.

## 7. Stop

Leave the other dates on the laptop. Leave `uploaded` false in the manifests until this one file is visible in the volume and the sizes match. Local CSVs stay. The manifest stays either way.

`databricks.yml` is the next file, and it records the catalog name from step 2. Bronze tables are a later phase.
