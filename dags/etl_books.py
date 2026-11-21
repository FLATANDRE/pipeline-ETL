from datetime import datetime, timedelta, timezone
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id="demo_etl_books",
    description="CSV/TXT -> PySpark transform -> Iceberg/SILO -> Trino validation",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule=None, catchup=False, max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(seconds=15)},
    tags=["etl", "iceberg", "silo", "polaris"],
) as dag:
    extract = BashOperator(task_id="extract_files", bash_command="cd /opt/lab && python -m app.extract", do_xcom_push=False)
    transform_load = BashOperator(task_id="transform_then_load", bash_command="cd /opt/lab && python -m app.transform_load", do_xcom_push=False)
    validate = BashOperator(task_id="validate_with_trino", bash_command="cd /opt/lab && python -m app.validate", do_xcom_push=False)
    extract >> transform_load >> validate
