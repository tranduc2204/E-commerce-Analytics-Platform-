"""Smoke test: mọi DAG import được, không cycle, có đủ task mong đợi.

Bắt lỗi cú pháp/import trước khi scheduler âm thầm không load DAG.
Không cần Airflow metadata DB — chỉ parse file DAG.
"""

from pathlib import Path

import pytest

DAG_DIR = Path(__file__).resolve().parents[1] / "dags"


@pytest.fixture(scope="module")
def dagbag():
    from airflow.models.dagbag import DagBag

    return DagBag(dag_folder=str(DAG_DIR), include_examples=False)


def test_no_import_errors(dagbag):
    assert not dagbag.import_errors, f"DAG import lỗi: {dagbag.import_errors}"


def test_daily_dag_loaded(dagbag):
    dag = dagbag.get_dag("olist_daily")
    assert dag is not None


def test_daily_dag_task_chain(dagbag):
    dag = dagbag.get_dag("olist_daily")
    assert {t.task_id for t in dag.tasks} == {
        "replay",
        "load_sync_partitions",
        "dbt_build",
    }
    # thứ tự replay → load → dbt
    load = dag.get_task("load_sync_partitions")
    assert "replay" in {t.task_id for t in load.upstream_list}
    assert "dbt_build" in {t.task_id for t in load.downstream_list}
