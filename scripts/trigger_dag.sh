#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec -T airflow airflow dags unpause demo_etl_books
docker compose exec -T airflow airflow dags trigger demo_etl_books
