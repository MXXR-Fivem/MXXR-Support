#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/docker/.env.api"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.bot-stack.yml"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}" >&2
  echo "Create it from deploy/docker/.env.api.example first." >&2
  exit 1
fi

cd "${ROOT_DIR}"

if docker compose version >/dev/null 2>&1; then
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
elif command -v docker-compose >/dev/null 2>&1; then
  docker-compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
else
  echo "Neither 'docker compose' nor 'docker-compose' is available." >&2
  exit 1
fi
