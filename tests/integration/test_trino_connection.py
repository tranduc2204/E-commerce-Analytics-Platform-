"""Integration: cần `make up`. Trino sống + 2 catalog raw/iceberg hiện diện."""

import pytest

from utils.trino_client import run_query

pytestmark = pytest.mark.integration


def test_select_one():
    assert run_query("SELECT 1") == [(1,)]


def test_catalogs_present():
    catalogs = {row[0] for row in run_query("SHOW CATALOGS")}
    assert {"raw", "iceberg"} <= catalogs
