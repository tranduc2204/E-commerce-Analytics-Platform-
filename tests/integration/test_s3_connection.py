"""Integration: cần `make up`. Kiểm tra MinIO connect + ghi/đọc 1 file."""

import uuid

import pandas as pd
import pytest

from utils.config import get_settings
from utils.s3_client import get_s3_client, upload_parquet

pytestmark = pytest.mark.integration


def test_bucket_exists():
    settings = get_settings()
    client = get_s3_client(settings)
    buckets = [b["Name"] for b in client.list_buckets()["Buckets"]]
    assert settings.lake_bucket in buckets


def test_write_and_read_parquet():
    settings = get_settings()
    client = get_s3_client(settings)
    key = f"raw/_smoke/{uuid.uuid4().hex}.parquet"
    df = pd.DataFrame({"a": [1, 2, 3]})
    upload_parquet(df, settings.lake_bucket, key, client=client)
    obj = client.get_object(Bucket=settings.lake_bucket, Key=key)
    assert obj["ContentLength"] > 0
    client.delete_object(Bucket=settings.lake_bucket, Key=key)
