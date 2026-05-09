#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

section() {
  printf '\n== %s ==\n' "$1"
}

section "Git Branch"
git branch --show-current 2>/dev/null || echo "git branch unavailable"

section "Git Status"
git status --short 2>/dev/null || echo "git status unavailable"

section "Running Containers"
if command -v docker >/dev/null 2>&1; then
  docker compose ps 2>/dev/null || docker ps
else
  echo "docker unavailable"
fi

section "Latest Roadmap Recommendation"
awk '/^### Immediate next sprint recommendation/{flag=1; count=0; next} flag && count < 18 {print; count++}' runbooks/ROADMAP.md 2>/dev/null || echo "ROADMAP.md unavailable"

section "Latest Sprint History"
tail -80 logs/sprints/sprint_history.md 2>/dev/null || echo "No sprint history ledger yet"
