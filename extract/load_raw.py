"""Bước Load: đăng ký partition mới với hive metastore sau khi replay ghi xong.

Hive external table không tự thấy partition mới trên S3 — phải gọi
sync_partition_metadata. Đây là bước "L" tách bạch trong ELT.

Chạy: python -m extract.load_raw            # sync các bảng daily
      python -m extract.load_raw --all     # sync cả bảng bootstrap
"""

import argparse
import sys

from extract.replay import BOOTSTRAP_TABLES, DAILY_TABLES
from utils.log import get_logger
from utils.trino_client import sync_raw_partitions

logger = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="sync cả bảng bootstrap")
    args = parser.parse_args()

    tables = DAILY_TABLES + (BOOTSTRAP_TABLES if args.all else [])
    logger.info("Sync partition metadata: %s", tables)
    sync_raw_partitions(tables)
    logger.info("Xong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
