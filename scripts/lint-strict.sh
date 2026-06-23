#!/usr/bin/env bash
# Строгие структурные правила ruff на изменённых файлах vs base (ratchet).
# Используется в CI (informational на время Фазы 0). Локальный гардрейл — pre-commit хук ruff-strict.
set -euo pipefail
BASE="${1:-origin/master}"
MERGE_BASE="$(git merge-base "$BASE" HEAD 2>/dev/null || echo "$BASE")"
EXCLUDE_RE='(/migrations/|/alembic/|xray_api/|/dashboard/build/)'

mapfile -t files < <(
  git diff --name-only --diff-filter=ACM "${MERGE_BASE}...HEAD" -- '*.py' \
    | grep -vE "$EXCLUDE_RE" || true
)

if [ "${#files[@]}" -eq 0 ]; then
  echo "lint-strict: изменённых .py нет — пропуск."
  exit 0
fi

echo "lint-strict: проверяю ${#files[@]} файл(ов) против ${MERGE_BASE}…"
uv run ruff check --config ruff-strict.toml "${files[@]}"
