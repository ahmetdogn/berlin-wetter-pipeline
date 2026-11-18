from pathlib import Path

from airflow.models import DagBag

DAG_FOLDER = Path(__file__).parent.parent / "dags"


def get_dag():
    bag = DagBag(dag_folder=str(DAG_FOLDER), include_examples=False)
    assert bag.import_errors == {}
    return bag.get_dag("wetter_ingest")


def test_dag_loads():
    dag = get_dag()
    assert dag is not None
    assert dag.catchup


def test_task_order():
    dag = get_dag()
    assert {t.task_id for t in dag.tasks} == {"get_stations", "fetch", "load", "check", "daily_agg"}
    assert dag.get_task("fetch").upstream_task_ids == {"get_stations"}
    assert dag.get_task("load").upstream_task_ids == {"fetch"}
    assert dag.get_task("daily_agg").upstream_task_ids == {"check"}
