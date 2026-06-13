"""Tải dataset Olist từ Kaggle về DATA_DIR.

Yêu cầu: pip install kaggle + đặt API token tại ~/.kaggle/kaggle.json
(Kaggle → Settings → Create New Token).
Không có token thì tải tay từ:
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
rồi giải nén vào DATA_DIR.

Chạy: python -m extract.download_olist
"""

import subprocess
import sys
from pathlib import Path

from utils.config import get_settings
from utils.log import get_logger

logger = get_logger(__name__)

KAGGLE_DATASET = "olistbr/brazilian-ecommerce"

EXPECTED_FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
]


def missing_files(data_dir: str | Path) -> list[str]:
    """Trả về danh sách file còn thiếu trong data_dir."""
    data_dir = Path(data_dir)
    return [f for f in EXPECTED_FILES if not (data_dir / f).exists()]


def download(data_dir: str | Path) -> None:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["kaggle", "datasets", "download", "-d", KAGGLE_DATASET,
         "-p", str(data_dir), "--unzip"],
        check=True,
    )


def main() -> int:
    settings = get_settings()
    if not missing_files(settings.data_dir):
        logger.info("Dataset đã đầy đủ trong %s, bỏ qua tải.", settings.data_dir)
        return 0
    logger.info("Tải %s về %s ...", KAGGLE_DATASET, settings.data_dir)
    download(settings.data_dir)
    still_missing = missing_files(settings.data_dir)
    if still_missing:
        logger.error("Tải xong nhưng vẫn thiếu: %s", still_missing)
        return 1
    logger.info("Hoàn tất — đủ %d file.", len(EXPECTED_FILES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
