"""DAG daily: replay 1 ngày → load (sync partition) → dbt build → alert khi fail.

Dùng execution_date của Airflow làm "ngày replay", nên backfill được:
    airflow dags backfill olist_daily -s 2017-01-01 -e 2017-12-31
"""

from __future__ import annotations

import pendulum
from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

REPO = "/opt/airflow/repo"

default_args = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": pendulum.duration(minutes=2),
}


def _replay(ds: str, **_):
    """Nhả dữ liệu của ngày {ds} lên raw zone."""
    from extract.replay import replay_day

    written = replay_day(ds)
    print(f"replay {ds}: ghi {written} bảng")


def _load(**_):
    """Sync partition metadata để Trino (raw file metastore) thấy dữ liệu vừa ghi."""
    from extract.replay import DAILY_TABLES
    from utils.trino_client import sync_raw_partitions

    sync_raw_partitions(DAILY_TABLES)


with DAG(
    dag_id="olist_daily",
    description="Olist ELT: extract → load → dbt build",
    schedule="@daily",
    start_date=pendulum.datetime(2017, 1, 1, tz="UTC"),
    catchup=False,
    default_args=default_args,
    tags=["olist", "elt"],
) as dag:

    replay = PythonOperator(
        task_id="replay",
        python_callable=_replay,
    )

    load = PythonOperator(
        task_id="load_sync_partitions",
        python_callable=_load,
    )

    # dbt build = run + test + snapshot + seed trong 1 lệnh, fail-fast khi test đỏ
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {REPO}/dbt && "
            "dbt build --profiles-dir . --target dev"
        ),
        env={"DBT_PROFILES_DIR": f"{REPO}/dbt"},
        append_env=True,
    )

    replay >> load >> dbt_build
