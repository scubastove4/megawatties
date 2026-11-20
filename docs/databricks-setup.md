# Databricks setup

Free Edition workspace, CLI login, the `emi` schema and landing volume, one smoke copy, and the `dev` bundle. The smoke copy does not create tables, upload the rest of the landing zone, or delete anything on the laptop.

The catalog on this workspace is `workspace`. The schema is `emi`. The volume is `emi.landing`. No service principal, no token in the repo, and no second SQL warehouse.

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

The 10 November file is in the volume and its manifest has `uploaded` set to true. Leave the other dates on the laptop. Local CSVs stay. The manifests stay.

## 8. Create the bundle

Create `databricks.yml` at the repo root. The file format is in [Declarative Automation Bundles configuration](https://docs.databricks.com/aws/en/dev-tools/bundles/settings), and every key is listed in the [configuration reference](https://docs.databricks.com/aws/en/dev-tools/bundles/reference). It names the bundle, the one development target, and the catalog from step 2. It does not contain a token. The `megawatties` profile in `~/.databrickscfg` supplies the login.

```yaml
bundle:
  name: megawatties

variables:
  catalog:
    description: Unity Catalog catalog for this Free Edition workspace.
    default: workspace
  schema:
    description: Schema that holds the EMI landing volume.
    default: emi
  landing_volume:
    description: Volume that stores the staged CSVs.
    default: landing

sync:
  exclude:
    - .cursor/
    - docs/
    - src/capture/
    - README.md
    - .gitignore

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: https://dbc-ed37dda6-cb93.cloud.databricks.com
      profile: megawatties
```

Add this line to `.gitignore` so local bundle state is not committed:

```text
.databricks/
```

From the repo root, check the file:

```bash
databricks bundle validate --target dev --profile megawatties
```

Validation reads the file and checks that the profile can see the workspace. It does not upload files or create jobs. A successful check prints `Validation OK!` and a workspace path under your user folder.

Deploy only after that succeeds:

```bash
databricks bundle deploy --target dev --profile megawatties
```

Deploy with no jobs writes bundle state under `.databricks/` on the laptop and creates the development folder in the workspace. It does not create tables. Bronze tables are a later phase.

The `sync.exclude` list keeps laptop-only paths out of that folder. `.cursor/`, `docs/`, `src/capture/`, `README.md`, and `.gitignore` stay on the laptop. `src/shared/`, `src/log/`, and `pyproject.toml` still deploy. Ingestion will import `shared` and `log` on Databricks. Capture keeps running on the laptop.

## 9. Redeploy and check the files

From the repo root, deploy again so the exclude list takes effect:

```bash
databricks bundle deploy --target dev --profile megawatties
```

In the workspace, open `Users / smorello4@gmail.com / .bundle / megawatties / dev / files`.

These paths should be gone:

- `.cursor/`
- `docs/`
- `src/capture/`
- `README.md`
- `.gitignore`

These paths should still be there:

- `src/shared/`
- `src/log/`
- `pyproject.toml`
- `databricks.yml`

`artifacts` stays empty. This deploy still does not create a job or a table. The 10 November CSV stays where step 6 put it.

## 10. Stop

The smoke upload is done. One file is in `workspace.emi.landing`. The bundle deploys to the `dev` folder and leaves capture on the laptop. Leave the other dates on the laptop. Do not create a table.

Phase 1 still needs the Prefect schedule, on this feature branch. That work stays on the laptop:

- Prefect 3, local UI, timezone `Pacific/Auckland`.
- Polls at 9:30, 15:30, and 18:30.
- Each poll runs the existing capture download over the seven-day lookback.
- Local CSVs and manifests stay. A poll should record the same outcomes as a manual download: downloaded, unchanged, replaced, or restored.

Do not upload the other dates, trigger a Databricks job, or delete local CSVs in that work. Those wait for phase 2, with the bronze, silver, and gold tables. The job that reads this volume is part of that phase.
