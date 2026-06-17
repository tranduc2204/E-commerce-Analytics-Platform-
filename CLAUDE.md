# CLAUDE.md

File này cung cấp hướng dẫn cho Claude Code (claude.ai/code) khi làm việc với mã nguồn trong repo này.

## Đây là gì

E-commerce Analytics Platform — một **ELT lakehouse** mang tính học tập/portfolio dựng trên
dataset Olist (sàn TMĐT Brazil — Kaggle, ~100k đơn, 9 bảng). Stack được chọn theo kiểu
"hình hài production" và **cố ý dư thừa** so với khối lượng dữ liệu; mục tiêu là luyện modern
data stack và mô hình hoá domain, **không** phải hiệu năng thô. Xem `brain_storm.txt` để biết
lý do chọn stack.

Pipeline: **Python extract → MinIO (parquet, raw zone) → Trino + Iceberg → dbt transform → Airflow orchestration → Metabase BI.**

vì số lượng dữ liệu của tập dataset này có giới hạn nên. hãy giả lập nó là 1 một API của 1 hệ thống OLTP. tôi muốn nó được partition ra sau đó ingest từ từ thông qua airflow từng ngày

## Các lệnh

Toàn bộ hạ tầng chạy qua Docker Compose; `.env` được compose tự nạp (copy từ `.env.example`).

```bash
# Dựng toàn bộ stack (MinIO, Postgres, Nessie, Trino, Airflow, Metabase)
docker compose up -d

# Giao diện service:  MinIO console :9001 | Trino :8080 | Airflow :8088 | Metabase :3000 | Nessie API :19120

# Đăng ký schema raw + external table trong Trino (chạy 1 lần sau khi MinIO đã có prefix dữ liệu)
docker compose exec trino trino --catalog raw -f /sql/01_init_raw.sql
docker compose exec trino trino --catalog raw -f /sql/02_raw_tables.sql

# Extract: tải dataset, rồi replay từng ngày vào raw zone
python -m extract.download_olist
python -m extract.replay --bootstrap            # products/sellers/geolocation (1 lần)
python -m extract.replay --date 2017-05-15      # đơn của 1 ngày + các bảng con
python -m extract.load_raw                      # sync partition mới vào metastore

# dbt (chạy trong thư mục dbt/ — profiles.yml nằm ở đó, đọc các biến TRINO_*)
cd dbt && dbt deps && dbt build                 # seed + run + snapshot + test
dbt run --select stg_orders                     # một model
dbt run --select fct_orders+                     # một model và mọi thứ downstream
dbt test --select fct_orders                    # test cho một model
dbt snapshot                                    # chỉ chạy SCD2 scd_customers

# Test Python
pytest tests/unit airflow/tests                 # nhanh, không cần hạ tầng
pytest -m integration                           # cần `docker compose up` trước
pytest tests/unit/test_replay.py::test_missing_timestamp_belongs_to_no_day   # một test đơn lẻ
```

> Test integration được đánh dấu bằng `pytest.mark.integration` (đã đăng ký marker trong
> `pyproject.toml`). Nessie dùng image dựng sẵn `ghcr.io/projectnessie/nessie` nên **không có**
> build context riêng trong `docker/` (khác Hive Metastore cũ).

## Kiến trúc

### Hai catalog Trino — quyết định thiết kế cốt lõi
- **`raw`** (Hive connector, `docker/trino/etc/catalog/raw.properties`): external table phủ lên
  parquet mà `extract/replay.py` ghi vào `s3://lake/raw/<table>/`. **Mọi cột đều là `varchar`** —
  raw phản chiếu CSV nguyên trạng, chỉ đọc, bất biến. Định nghĩa trong `sql/02_raw_tables.sql`,
  partition theo `ingestion_date`. Metastore là **file-based** (`hive.metastore=file`,
  `hive.metastore.catalog.dir=s3://lake/raw-meta`) — không cần service riêng; `sync_partition_metadata`
  vẫn chạy bình thường.
- **`iceberg`** (`iceberg.properties`): vùng curated. dbt materialize mọi thứ vào đây.
  ACID, schema evolution, hidden partitioning. Catalog do **Nessie** (REST v2, `iceberg.catalog.type=nessie`,
  branch `main`) quản lý — sổ đăng ký bảng Iceberg "bảng nào nằm ở đâu".

**Không còn Hive Metastore service.** Hai catalog dùng **hai cơ chế catalog khác nhau** (Nessie cho
iceberg, file metastore cho raw) vì Nessie chỉ phục vụ Iceberg, không phủ được external Hive table.
**Không có warehouse riêng** — MinIO + Iceberg + Trino *chính là* warehouse (tách storage/compute).

### Mô phỏng "replay" — vì sao tồn tại
Olist là một dump lịch sử tĩnh (2016–2018). `extract/replay.py` biến nó thành luồng: mỗi lần
chạy sẽ cắt lát các đơn theo `order_purchase_timestamp` cho một ngày và ghi lát của ngày đó
(cùng order_items/payments/reviews/customers liên quan) thành một partition mới. Đây chính là
thứ làm cho incremental model, snapshot và source freshness của dbt trở nên *có ý nghĩa* thay vì
chỉ trang trí. Airflow DAG điều khiển nó qua `execution_date`, nên backfill sẽ replay lại lịch sử.

Quyết định logic nghiệp vụ then chốt mã hoá trong `slice_for_date()`: **đơn thiếu
`order_purchase_timestamp` không thuộc về ngày nào và không bao giờ vào lake** (được khoá bởi
`tests/unit/test_replay.py`). Các bảng con được lọc theo `order_id` của ngày đó để giữ toàn vẹn
tham chiếu trong từng lát cắt.

### Load là một bước riêng biệt
External table (file metastore) không tự phát hiện partition mới trên S3. Sau khi replay ghi parquet,
`extract/load_raw.py` (và task `load_sync_partitions` của DAG) gọi `sync_partition_metadata` thông
qua `utils/trino_client.sync_raw_partitions()`. Đây là chữ "L" trong ELT.

### Phân tầng dbt (`dbt/models/`)
> Lưu ý Nessie: Trino **không tạo được view** trên Iceberg Nessie catalog, nên staging và
> intermediate materialize thành **table** (cấu hình ở `dbt_project.yml`), không phải view.
- **staging/** (table): một model cho mỗi source, cast `varchar` → kiểu thật bằng
  `cast(nullif(col, '') as timestamp)`. Olist dùng định dạng dấu cách `YYYY-MM-DD HH:MM:SS`
  (**không** phải ISO-8601 có chữ `T`), nên không dùng `from_iso8601_timestamp`.
  **Mọi việc cast kiểu xảy ra ở đây**, không ở đâu khác phía trên.
- **intermediate/** (table): nắn các bảng con về **grain đơn hàng** (`int_order_items_agg`,
  `int_order_payments_agg`) và dedup review về một-dòng-mỗi-đơn (`int_order_reviews_dedup`).
- **marts/** (table): star schema. `fct_orders` (grain = 1 đơn) và `fct_order_items`
  (grain = order_id + order_item_id) dùng **incremental merge** với cửa sổ lookback 3 ngày và
  partition Iceberg `month(order_purchase_timestamp)`. `dim_customers` được dựng từ snapshot SCD2
  (các dòng hiện hành = `dbt_valid_to is null`).

Các quy tắc domain quan trọng: **GMV loại trừ đơn `canceled`/`unavailable`** (`fct_orders.gmv`);
`is_late_delivery` là **null** khi thiếu ngày giao (~3% số đơn) thay vì ép thành true/false.
`mart_monthly_gmv` trả lời các câu hỏi nghiệp vụ chủ chốt (GMV theo tháng, lũy kế, tăng trưởng
MoM, tỷ lệ huỷ/giao trễ).

`dim_customers` lấy khoá là **`customer_unique_id`** (người thật), không phải `customer_id`
(Olist cấp theo từng đơn). Snapshot SCD2 (`snapshots/scd_customers.sql`, strategy `check` trên
zip/city/state) theo dõi việc khách đổi địa chỉ qua các đơn.

### Package dùng chung `utils/`
`utils/` là nguồn sự thật duy nhất cho mọi kết nối hạ tầng (`config.py` → `Settings` từ env,
`s3_client.py`, `trino_client.py`, `log.py`). `extract/`, Airflow DAG và test đều import từ đây —
không bao giờ nhân bản logic kết nối. Compose mount nó vào container Airflow tại
`/opt/airflow/repo/utils` với `PYTHONPATH=/opt/airflow/repo`.

### Tính hai mặt của hostname — footgun số 1
Bên trong mạng Docker, các service gọi nhau bằng tên service (`minio:9000`, `trino:8080`,
`nessie:19120`). Từ máy host thì là `localhost` + port được map. Mọi endpoint đi qua biến
môi trường (`.env` khi chạy ở host, khối `environment:` của compose cho container Airflow) —
**không bao giờ hardcode host**. File catalog của Trino đọc credential MinIO qua
`${ENV:MINIO_ROOT_USER}` / `${ENV:MINIO_ROOT_PASSWORD}`, được tiêm vào trong service `trino` của compose.

### Một Postgres phục vụ ba database
Một container Postgres chứa `nessie_db` (version store của Nessie), `airflow_db` và `metabase_db`
(tạo bởi `docker/postgres/init-dbs.sql`) để tiết kiệm bộ nhớ.

## Ranh giới test (giữ chúng tách biệt)
- `tests/` — chỉ logic code Python (unit = không cần hạ tầng; integration = cần stack đang chạy).
- `dbt/models/**/*.yml` — chất lượng **dữ liệu** (schema test, relationship, accepted range, freshness).
- `airflow/tests/` — tính toàn vẹn DAG (import sạch, không cycle, đủ tập task).



Lỗi ở mỗi nơi chỉ về một tầng khác nhau; đừng gộp chúng lại.

## Ghi chú về seed
`dbt/seeds/product_category_name_translation.csv` hiện chỉ chứa danh sách category **một phần**.
Bản dịch đầy đủ đi kèm khi tải từ Kaggle — hãy thay seed bằng file đầy đủ đó.
