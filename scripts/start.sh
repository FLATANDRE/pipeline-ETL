#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .env ]]; then cp .env.example .env; fi
docker compose config --quiet
docker compose build lab-init
docker compose up -d
printf '\nAcompanhe: docker compose logs -f lab-init airflow\n'
