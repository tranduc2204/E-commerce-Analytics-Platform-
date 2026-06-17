"""Factory kết nối Trino + helper chạy query — dùng chung cho extract, DAG, tests."""

import trino

from utils.config import Settings, get_settings


def get_connection(
    settings: Settings | None = None,
    catalog: str = "iceberg",
    schema: str = "analytics",
):
    settings = settings or get_settings()
    return trino.dbapi.connect(
        host=settings.trino_host,
        port=settings.trino_port,
        user=settings.trino_user,
        catalog=catalog,
        schema=schema,
    )


def run_query(sql: str, settings: Settings | None = None, catalog: str = "iceberg") -> list[tuple]:
    conn = get_connection(settings, catalog=catalog)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        conn.close()


def sync_raw_partitions(tables: list[str], settings: Settings | None = None) -> None:
    """Báo cho file metastore (raw) biết các partition mới mà replay vừa ghi lên MinIO."""
    for table in tables:
        run_query(
            f"CALL raw.system.sync_partition_metadata('olist', '{table}', 'ADD')",
            settings=settings,
            catalog="raw",
        )
