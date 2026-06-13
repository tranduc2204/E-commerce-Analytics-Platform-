"""Unit test load cấu hình từ env."""

import pytest

from utils.config import get_settings


def test_defaults_when_env_absent(monkeypatch):
    for var in ["MINIO_ENDPOINT", "TRINO_HOST", "TRINO_PORT", "LAKE_BUCKET"]:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("utils.config.load_dotenv", lambda *a, **k: None)
    s = get_settings()
    assert s.trino_host == "localhost"
    assert s.trino_port == 8080
    assert s.lake_bucket == "lake"


def test_reads_from_env(monkeypatch):
    monkeypatch.setattr("utils.config.load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("TRINO_HOST", "trino")
    monkeypatch.setenv("TRINO_PORT", "9999")
    monkeypatch.setenv("LAKE_BUCKET", "mybucket")
    s = get_settings()
    assert s.trino_host == "trino"
    assert s.trino_port == 9999
    assert s.lake_bucket == "mybucket"


def test_port_is_int(monkeypatch):
    monkeypatch.setattr("utils.config.load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("TRINO_PORT", "8080")
    assert isinstance(get_settings().trino_port, int)
