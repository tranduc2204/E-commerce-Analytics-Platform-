# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

E-commerce Analytics Platform — a learning/portfolio **ELT lakehouse** over the Olist
Brazilian e-commerce dataset (Kaggle, ~100k orders, 9 tables). The stack is deliberately
"production-shaped" and over-provisioned for the data volume; the goal is to practice the
modern data stack and domain modeling, not raw performance. See `brain_storm.txt` for the
stack rationale.

Pipeline: **Python extract → MinIO (parquet, raw zone) → Trino + Iceberg → dbt transform → Airflow orchestration → Metabase BI.**

> **Gotcha:** the project directory name has a **trailing space** (`E-commerce_Analytics_Platform `).
> This breaks Docker volume mounts and many path operations. Quote paths everywhere, or rename
> the directory to drop the trailing space before doing infra work.

## Commands

All infra runs via Docker Compose; `.env` is auto-loaded by compose (copy from `.env.example`).

```bash
# Bring up the whole stack (MinIO, Postgres, Hive Metastore, Trino, Airflow, Metabase)
docker compose up -d

# Service UIs:  MinIO console :9001 | Trino :8080 | Airflow :8088 | Metabase :3000

# Register raw schema + external tables in Trino (run once after MinIO has data prefixes)
docker compose exec trino trino --catalog raw -f /sql/01_init_raw.sql
docker compose exec trino trino --catalog raw -f /sql/02_raw_tables.sql

# Extract: download dataset, then replay it day-by-day into the raw zone
python -m extract.download_olist
python -m extract.replay --bootstrap            # products/sellers/geolocation (once)
python -m extract.replay --date 2017-05-15      # one day's orders + children
python -m extract.load_raw                      # sync new partitions to the metastore

# dbt (run from dbt/ — profiles.yml lives there, reads TRINO_* env vars)
cd dbt && dbt deps && dbt build                 # seed + run + snapshot + test
dbt run --select stg_orders                     # one model
dbt run --select fct_orders+                     # a model and everything downstream
dbt test --select fct_orders                    # tests for one model
dbt snapshot                                    # SCD2 scd_customers only

# Python tests
pytest tests/unit airflow/tests                 # fast, no infra needed
pytest -m integration                           # needs `docker compose up` first
pytest tests/unit/test_replay.py::test_missing_timestamp_belongs_to_no_day   # single test
```

> Integration tests are marked with `pytest.mark.integration`. There is no `pyproject.toml`
> yet, so register the marker there (or expect an "unknown marker" warning). `Makefile`,
> `pyproject.toml`, the `docker/hive-metastore/` build context, and `.github/workflows/ci.yml`
> are referenced in the plan (`brain_storm.txt`) but **not yet created**.

## Architecture

### Two Trino catalogs — the core design decision
- **`raw`** (Hive connector, `docker/trino/etc/catalog/raw.properties`): external tables over
  parquet that `extract/replay.py` writes to `s3://lake/raw/<table>/`. **Every column is
  `varchar`** — raw mirrors the CSV verbatim, read-only, immutable. Defined in
  `sql/02_raw_tables.sql`, partitioned by `ingestion_date`.
- **`iceberg`** (`iceberg.properties`): the curated zone. dbt materializes everything here.
  ACID, schema evolution, hidden partitioning.

Both share one Hive Metastore as catalog. There is **no separate warehouse** — MinIO + Iceberg
+ Trino *is* the warehouse (storage/compute separation).

### The "replay" simulation — why it exists
Olist is a static historical dump (2016–2018). `extract/replay.py` turns it into a stream:
each run slices orders by `order_purchase_timestamp` for one date and writes that day's slice
(plus the related order_items/payments/reviews/customers) as a new partition. This is what
makes dbt incremental models, snapshots, and source freshness *meaningful* instead of
decorative. The Airflow DAG drives it via `execution_date`, so backfill replays history.

Key business-logic decision encoded in `slice_for_date()`: **orders with a missing
`order_purchase_timestamp` belong to no day and never enter the lake** (locked by
`tests/unit/test_replay.py`). Child tables are filtered by the day's `order_id`s to preserve
referential integrity within each slice.

### Load is a distinct step
Hive external tables don't auto-discover new S3 partitions. After replay writes parquet,
`extract/load_raw.py` (and the DAG's `load_sync_partitions` task) calls
`sync_partition_metadata` via `utils/trino_client.sync_raw_partitions()`. This is the "L" in ELT.

### dbt layering (`dbt/models/`)
- **staging/** (views): one model per source, casts `varchar` → typed using
  `from_iso8601_timestamp(nullif(col, ''))`. **All type casting happens here**, nowhere upstream.
- **intermediate/** (views): reshape child tables to **order grain** (`int_order_items_agg`,
  `int_order_payments_agg`) and dedup reviews to one-per-order (`int_order_reviews_dedup`).
- **marts/** (tables): star schema. `fct_orders` (grain = 1 order) and `fct_order_items`
  (grain = order_id + order_item_id) are **incremental merge** with a 3-day lookback window
  and Iceberg `month(order_purchase_timestamp)` partitioning. `dim_customers` is built from
  the SCD2 snapshot (current rows = `dbt_valid_to is null`).

Domain rules that matter: **GMV excludes `canceled`/`unavailable` orders** (`fct_orders.gmv`);
`is_late_delivery` is **null** when the delivery date is missing (~3% of orders) rather than
forced true/false. `mart_monthly_gmv` answers the headline business questions (monthly GMV,
running total, MoM growth, cancel/late rates).

`dim_customers` is keyed on **`customer_unique_id`** (the real person), not `customer_id`
(which Olist issues per-order). The SCD2 snapshot (`snapshots/scd_customers.sql`, `check`
strategy on zip/city/state) tracks address changes across orders.

### Shared `utils/` package
`utils/` is the single source of truth for all infra connections (`config.py` → `Settings`
from env, `s3_client.py`, `trino_client.py`, `log.py`). `extract/`, the Airflow DAG, and
tests all import from it — never duplicate connection logic. Compose mounts it into the
Airflow container at `/opt/airflow/repo/utils` with `PYTHONPATH=/opt/airflow/repo`.

### Hostname duality — the #1 footgun
Inside the Docker network, services reach each other by service name (`minio:9000`,
`trino:8080`, `hive-metastore:9083`). From the host, it's `localhost` + mapped port. Every
endpoint flows through env vars (`.env` for host runs, compose `environment:` blocks for the
Airflow container) — **never hardcode a host**. Trino catalog files read MinIO credentials via
`${ENV:MINIO_ROOT_USER}` / `${ENV:MINIO_ROOT_PASSWORD}`, injected in the `trino` compose service.

### Postgres serves three databases
One Postgres container hosts `metastore_db`, `airflow_db`, and `metabase_db` (created by
`docker/postgres/init-dbs.sql`) to save memory.

## Test boundaries (keep these separate)
- `tests/` — Python code logic only (unit = no infra; integration = needs the stack up).
- `dbt/models/**/*.yml` — **data** quality (schema tests, relationships, accepted ranges, freshness).
- `airflow/tests/` — DAG integrity (imports cleanly, no cycle, expected task set).

A failure in each points at a different layer; don't merge them.

## Note on the seed
`dbt/seeds/product_category_name_translation.csv` currently holds a **partial** category list.
The full translation ships with the Kaggle download — replace the seed with that complete file.
