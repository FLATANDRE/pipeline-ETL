#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/run.sh
docker compose exec -T airflow python -m app.failure_demo
# Retry on the unchanged source must keep the expected logical rows, not duplicate them.
docker compose exec -T airflow python -m app.extract
docker compose exec -T airflow python -m app.transform_load
docker compose exec -T airflow python -m app.validate
