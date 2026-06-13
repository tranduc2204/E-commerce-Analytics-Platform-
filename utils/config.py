"""Cấu hình tập trung: mọi kết nối (MinIO, Trino) đọc từ đây, không hardcode.

Giá trị lấy từ biến môi trường (file .env ở root khi chạy local;
docker-compose bơm trực tiếp env khi chạy trong container Airflow).
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    lake_bucket: str
    trino_host: str
    trino_port: int
    trino_user: str
    data_dir: str


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        minio_endpoint=os.environ.get("MINIO_ENDPOINT", "http://localhost:9000"),
        minio_access_key=os.environ.get("MINIO_ROOT_USER", "admin"),
        minio_secret_key=os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin123"),
        lake_bucket=os.environ.get("LAKE_BUCKET", "lake"),
        trino_host=os.environ.get("TRINO_HOST", "localhost"),
        trino_port=int(os.environ.get("TRINO_PORT", "8080")),
        trino_user=os.environ.get("TRINO_USER", "dbt"),
        data_dir=os.environ.get("DATA_DIR", "./data"),
    )
