#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs/sprints

TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
BRANCH="$(git branch --show-current 2>/dev/null || echo unknown)"
CHANGED_FILES="$(git status --short 2>/dev/null | sed 's/^/- `/' | sed 's/$/`/' || true)"
VERIFY_SUMMARY="$(tail -40 logs/verification/verification_history.md 2>/dev/null | sed 's/```/~~~/' || echo 'No verification ledger entries yet.')"

{
  printf '\n## %s - Sprint Closeout Snapshot\n\n' "$TIMESTAMP"
  printf -- '- Commit: `%s`\n' "$COMMIT"
  printf -- '- Branch: `%s`\n' "$BRANCH"
  printf -- '- Executor: Codex/operator\n'
  printf -- '- Files changed:\n'
  if [ -n "$CHANGED_FILES" ]; then
    printf '%s\n' "$CHANGED_FILES"
  else
    printf '  - none\n'
  fi
  printf -- '- Verification:\n'
  printf '  ```text\n'
  printf '%s\n' "$VERIFY_SUMMARY" | sed 's/^/  /'
  printf '  ```\n'
  printf -- '- Known issues:\n'
  printf '  - See `runbooks/known_issues.md`.\n'
  printf -- '- Next:\n'
  printf '  - Follow `runbooks/ROADMAP.md` immediate next sprint recommendation unless operator overrides.\n'
} >> logs/sprints/sprint_history.md

printf 'Appended sprint closeout snapshot to logs/sprints/sprint_history.md\n'
