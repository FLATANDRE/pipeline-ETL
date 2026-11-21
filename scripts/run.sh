#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# CLI alternative: executes the SAME modules as the DAG, not an Airflow DAG run.
# Never run this concurrently with a DAG using the same state directory.
docker compose exec -T airflow python -m app.doctor
docker compose exec -T airflow python -m app.extract
docker compose exec -T airflow python -m app.transform_load
docker compose exec -T airflow python -m app.validate
