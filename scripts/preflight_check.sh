#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FAILURES=0

pass() { printf 'PASS: %s\n' "$1"; }
warn() { printf 'WARN: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; FAILURES=$((FAILURES + 1)); }

if docker info >/dev/null 2>&1; then
  pass "Docker is running"
else
  fail "Docker is not reachable"
fi

if [ -f .env ]; then
  pass ".env exists"
elif [ -f .env.example ]; then
  warn ".env missing; .env.example exists and Compose defaults are available"
else
  fail "No .env or .env.example file found"
fi

check_health() {
  local service="$1"
  local status
  status="$(docker compose ps "$service" --format '{{.Health}}' 2>/dev/null | head -1)"
  if [ "$status" = "healthy" ]; then
    pass "$service container is healthy"
  else
    fail "$service container health is '${status:-unknown}'"
  fi
}

check_health postgres
check_health redis

if docker compose ps hydra-console --status running >/dev/null 2>&1 && docker compose ps hydra-console --status running | grep -q hydra-console; then
  pass "hydra-console container is running"
else
  fail "hydra-console container is not running"
fi

if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-hydra}" -d "${POSTGRES_DB:-hydra}" >/dev/null 2>&1; then
  pass "Postgres is reachable"
else
  fail "Postgres is not reachable"
fi

if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
  pass "Redis is reachable"
else
  fail "Redis is not reachable"
fi

if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
  pass "FastAPI /health is reachable"
else
  fail "FastAPI /health is not reachable"
fi

if [ "$FAILURES" -eq 0 ]; then
  printf '\nPREFLIGHT PASS\n'
  exit 0
fi

printf '\nPREFLIGHT FAIL (%s failure(s))\n' "$FAILURES"
exit 1
