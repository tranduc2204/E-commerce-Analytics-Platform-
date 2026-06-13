"""Replay: giả lập nguồn dữ liệu phát sinh hàng ngày từ dump lịch sử Olist.

Mỗi lần chạy với --date YYYY-MM-DD sẽ "nhả" các đơn mua trong ngày đó
(cùng items/payments/reviews/customers liên quan) thành parquet lên
s3://<bucket>/raw/<table>/ingestion_date=<date>/data.parquet

--bootstrap ghi các bảng ít biến động (products, sellers, geolocation)
một lần duy nhất với ingestion_date=1900-01-01.

Quyết định xử lý dữ liệu bẩn (document cho dbt docs):
- Đơn thiếu order_purchase_timestamp KHÔNG thuộc về ngày nào → replay bỏ qua,
  không bao giờ vào lake. Với Olist thực tế cột này không null nên không mất dữ liệu;
  unit test chốt hành vi này để thay dataset khác vẫn an toàn.
- Reviews lọc theo order_id của đơn mua trong ngày (không theo review_creation_date)
  — chấp nhận review "đến sớm" so với thực tế để giữ tính toàn vẹn tham chiếu.

Chạy:  python -m extract.replay --date 2017-05-15
       python -m extract.replay --bootstrap
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from utils.config import Settings, get_settings
from utils.log import get_logger
from utils.s3_client import get_s3_client, upload_parquet

logger = get_logger(__name__)

BOOTSTRAP_DATE = "1900-01-01"

CSV_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
}

DAILY_TABLES = ["orders", "order_items", "order_payments", "order_reviews", "customers"]
BOOTSTRAP_TABLES = ["products", "sellers", "geolocation"]


def load_csv(table: str, data_dir: str | Path) -> pd.DataFrame:
    """Đọc CSV nguyên trạng: mọi cột là string — cast kiểu là việc của dbt staging."""
    return pd.read_csv(Path(data_dir) / CSV_FILES[table], dtype=str)


def slice_for_date(dfs: dict[str, pd.DataFrame], run_date: str) -> dict[str, pd.DataFrame]:
    """Cắt lát dữ liệu của một ngày theo order_purchase_timestamp.

    Logic thuần — không chạm mạng/đĩa — để unit test được.
    """
    orders = dfs["orders"]
    # .str[:10] với NaN trả NaN, so sánh == luôn False → đơn thiếu timestamp bị loại
    day_orders = orders[orders["order_purchase_timestamp"].str[:10] == run_date]
    order_ids = set(day_orders["order_id"])
    customer_ids = set(day_orders["customer_id"])

    return {
        "orders": day_orders,
        "order_items": dfs["order_items"][dfs["order_items"]["order_id"].isin(order_ids)],
        "order_payments": dfs["order_payments"][dfs["order_payments"]["order_id"].isin(order_ids)],
        "order_reviews": dfs["order_reviews"][dfs["order_reviews"]["order_id"].isin(order_ids)],
        "customers": dfs["customers"][dfs["customers"]["customer_id"].isin(customer_ids)],
    }


def write_slice(
    slices: dict[str, pd.DataFrame], ingestion_date: str, settings: Settings, client=None
) -> int:
    """Ghi các lát cắt lên raw zone; partition rỗng thì bỏ qua. Trả về số bảng đã ghi."""
    client = client or get_s3_client(settings)
    written = 0
    for table, df in slices.items():
        if df.empty:
            logger.info("%s: 0 dòng cho %s — bỏ qua.", table, ingestion_date)
            continue
        key = f"raw/{table}/ingestion_date={ingestion_date}/data.parquet"
        uri = upload_parquet(df, settings.lake_bucket, key, client=client)
        logger.info("%s: %d dòng → %s", table, len(df), uri)
        written += 1
    return written


def replay_day(run_date: str, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    dfs = {t: load_csv(t, settings.data_dir) for t in DAILY_TABLES}
    slices = slice_for_date(dfs, run_date)
    return write_slice(slices, run_date, settings)


def bootstrap(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    slices = {t: load_csv(t, settings.data_dir) for t in BOOTSTRAP_TABLES}
    return write_slice(slices, BOOTSTRAP_DATE, settings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, help="ngày replay, YYYY-MM-DD")
    parser.add_argument("--bootstrap", action="store_true",
                        help="ghi products/sellers/geolocation một lần")
    args = parser.parse_args()

    if not args.date and not args.bootstrap:
        parser.error("cần --date hoặc --bootstrap")
    if args.bootstrap:
        bootstrap()
    if args.date:
        replay_day(args.date.isoformat())
    return 0


if __name__ == "__main__":
    sys.exit(main())
