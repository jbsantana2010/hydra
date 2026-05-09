#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
elif [ -f .env.example ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env.example
  set +a
  echo "WARN: .env missing; validated values from .env.example/defaults"
else
  echo "WARN: neither .env nor .env.example exists"
fi

MISSING=0

check_var() {
  local name="$1"
  local value="${!name:-}"
  if [ -n "$value" ]; then
    echo "PASS: $name is set"
  else
    echo "WARN: $name is missing"
    MISSING=$((MISSING + 1))
  fi
}

check_var POSTGRES_DB
check_var POSTGRES_USER
check_var POSTGRES_PASSWORD
check_var HYDRA_BASIC_USER
check_var HYDRA_BASIC_PASS

if [ "$MISSING" -eq 0 ]; then
  echo "ENV VALIDATION PASS"
else
  echo "ENV VALIDATION WARN: $MISSING value(s) missing"
fi
