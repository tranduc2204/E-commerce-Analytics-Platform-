"""Factory kết nối MinIO/S3 — nơi duy nhất trong repo tạo client S3."""

import io

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from botocore.config import Config

from utils.config import Settings, get_settings


def get_s3_client(settings: Settings | None = None):
    settings = settings or get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(s3={"addressing_style": "path"}),
        region_name="us-east-1",
    )


def upload_parquet(df: pd.DataFrame, bucket: str, key: str, client=None) -> str:
    """Ghi DataFrame thành 1 file parquet trên s3://bucket/key, trả về URI."""
    client = client or get_s3_client()
    buffer = io.BytesIO()
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, buffer, compression="snappy")
    buffer.seek(0)
    client.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())
    return f"s3://{bucket}/{key}"
