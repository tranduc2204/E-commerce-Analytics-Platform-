# E-commerce Analytics Platform

ELT **lakehouse** học tập/portfolio trên dataset [Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
(sàn TMĐT Brazil, ~100k đơn, 9 bảng). Stack mang "hình hài production" và **cố ý dư thừa** so với
khối lượng dữ liệu — mục tiêu là luyện modern data stack + mô hình hoá domain.

```
Python extract → MinIO (parquet, raw zone) → Trino + Iceberg → dbt transform → Airflow → Metabase
```

## Stack

| Lớp           | Công nghệ                       | Vai trò                                              |
| ------------- | ------------------------------- | --------------------------------------------------- |
| Extract       | Python (pandas + pyarrow)       | Ingest CSV Olist, "replay" theo ngày, ghi parquet   |
| Storage       | MinIO (S3-compatible)           | Object storage chứa parquet                         |
| Table format  | Apache Iceberg                  | ACID, schema evolution, hidden partitioning         |
| Catalog       | Hive Metastore + Postgres       | Sổ đăng ký bảng cho cả `raw` (hive) lẫn `iceberg`   |
| Query engine  | Trino                           | SQL phân tán đọc/ghi Iceberg — thay vai warehouse   |
| Transform     | dbt (`dbt-trino`)               | staging → intermediate → marts, SCD2, incremental   |
| Orchestration | Airflow                         | DAG daily: replay → load → dbt build                |
| BI            | Metabase                        | Dashboard GMV, MoM, tỷ lệ huỷ/giao trễ              |
| Hạ tầng       | Docker Compose                  | ~7 service                                          |
| CI            | GitHub Actions                  | unit + DAG integrity + dbt parse trên mỗi PR        |

Không có warehouse riêng: **MinIO + Iceberg + Trino *chính là* warehouse** (tách storage/compute).

## Yêu cầu

- Docker + Docker Compose
- Python 3.10+ (để chạy extract & test ở host)
- Kaggle API token (`~/.kaggle/kaggle.json`) — hoặc tải dataset thủ công

## Quickstart

```bash
# 1. Cấu hình
cp .env.example .env

# 2. Môi trường Python (khuyến nghị venv)
python -m venv venv && source venv/bin/activate
make install                 # pip install -e ".[dev,dbt,extract]"

# 3. Dựng hạ tầng
make up                      # MinIO :9001 | Trino :8080 | Airflow :8088 | Metabase :3000

# 4. Lấy dữ liệu rồi nạp vào lake
make download                # tải Olist từ Kaggle về data/
make init-raw                # tạo schema + external table raw trong Trino
make bootstrap               # products/sellers/geolocation (1 lần)
make replay DATE=2017-05-15  # đơn của 1 ngày + bảng con
make load                    # sync partition mới vào metastore

# 5. Transform
make dbt-build               # seed + run + snapshot + test

# 6. BI: mở http://localhost:3000, nối Trino (xem "Metabase" bên dưới)
```

> Có thể replay nhiều ngày bằng vòng lặp, hoặc để Airflow backfill:
> `docker compose exec airflow airflow dags backfill olist_daily -s 2017-01-01 -e 2017-12-31`

## Test

```bash
make test               # unit + DAG integrity — nhanh, không cần hạ tầng
make test-integration   # cần `make up` (MinIO/Trino đang chạy)
```

Ranh giới test (giữ tách biệt):

- `tests/` — logic code Python (unit / integration).
- `dbt/models/**/*.yml` — chất lượng **dữ liệu** (schema test, relationship, range, freshness).
- `airflow/tests/` — tính toàn vẹn DAG (import sạch, không cycle, đủ task).

## Kiến trúc tóm tắt

- **Hai catalog Trino.** `raw` (hive, mọi cột `varchar`, bất biến) phủ lên parquet thô;
  `iceberg` là vùng curated dbt materialize vào.
- **Replay** biến dump tĩnh thành luồng theo ngày → incremental/snapshot/freshness của dbt có ý nghĩa.
  Đơn thiếu `order_purchase_timestamp` không thuộc ngày nào và không vào lake.
- **Load là bước riêng:** external table không tự thấy partition mới — `extract/load_raw.py` gọi
  `sync_partition_metadata`.
- **dbt:** staging (cast kiểu) → intermediate (về grain đơn) → marts (star schema). `fct_orders`/
  `fct_order_items` incremental merge, partition `month(order_purchase_timestamp)`. `dim_customers`
  dựng từ snapshot SCD2 theo `customer_unique_id`. GMV loại đơn `canceled`/`unavailable`.

Chi tiết đầy đủ: xem [CLAUDE.md](CLAUDE.md).

## Metabase

Driver Trino không đi kèm Metabase. Tải `starburst-*.metabase-driver.jar`
([release](https://github.com/starburstdata/metabase-driver/releases)) vào
`docker/metabase/plugins/` rồi `docker compose restart metabase`. Khi nối: host `trino`,
port `8080`, catalog `iceberg`, user bất kỳ.

## Cấu trúc thư mục

```
docker-compose.yml          # ~7 service
Makefile                    # phím tắt: make help
pyproject.toml              # deps + cấu hình pytest (marker integration)
docker/                     # cấu hình trino/airflow/postgres/metabase
utils/                      # package dùng chung: config, s3_client, trino_client, log
extract/                    # download_olist, replay, load_raw
sql/                        # DDL đăng ký raw schema + external table
dbt/                        # staging / intermediate / marts / snapshots / seeds
airflow/dags/               # olist_daily DAG  (+ airflow/tests/)
tests/                      # unit/ + integration/
.github/workflows/ci.yml    # CI
```
