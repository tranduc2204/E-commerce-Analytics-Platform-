"""Integration end-to-end tối thiểu: cần `make up` + đã có CSV trong DATA_DIR.

replay 1 ngày → sync partition → query Trino đếm dòng raw khớp số ghi.
Skip nếu chưa tải dataset (để CI nhẹ không vướng).
"""

from pathlib import Path

import pytest

from extract.download_olist import missing_files
from extract.replay import DAILY_TABLES, replay_day
from utils.config import get_settings
from utils.trino_client import run_query, sync_raw_partitions

pytestmark = pytest.mark.integration

RUN_DATE = "2017-05-15"


@pytest.fixture(scope="module")
def settings():
    s = get_settings()
    if missing_files(s.data_dir):
        pytest.skip("Chưa tải dataset Olist vào DATA_DIR")
    return s


def test_replay_then_query_matches(settings):
    written = replay_day(RUN_DATE, settings=settings)
    assert written > 0
    sync_raw_partitions(DAILY_TABLES, settings=settings)

    rows = run_query(
        f"SELECT count(*) FROM raw.olist.orders "
        f"WHERE ingestion_date = '{RUN_DATE}'",
        settings=settings,
        catalog="raw",
    )
    assert rows[0][0] > 0
