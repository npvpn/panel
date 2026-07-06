#!/usr/bin/env bash
#
# NPVPN-1585 — удаление нод, созданных create_nodes.sh.
#
# Читает id из IDS_FILE (по одному в строке) и удаляет каждую ноду
# через DELETE /api/node/{id}. Успешно удалённые id вычёркиваются из файла,
# так что скрипт можно перезапускать — останутся только неудалённые.
#
# Использование:
#   TOKEN="<bearer>" ./delete_nodes.sh
#
# Переменные окружения:
#   TOKEN     — Bearer-токен админа (ОБЯЗАТЕЛЬНО)
#   BASE_URL  — база API, напр. https://<panel-host>/api (ОБЯЗАТЕЛЬНО)
#   IDS_FILE  — файл со списком id (default: created_node_ids.txt)
#
set -uo pipefail

: "${TOKEN:?Задай TOKEN='<bearer>' — токен админа панели}"
: "${BASE_URL:?Задай BASE_URL='https://<panel-host>/api'}"
IDS_FILE="${IDS_FILE:-created_node_ids.txt}"

[ -f "$IDS_FILE" ] || { echo "Нет файла $IDS_FILE"; exit 1; }

total=$(grep -c '[0-9]' "$IDS_FILE" || true)
echo "Удаляю $total нод с $BASE_URL (из $IDS_FILE)"

remaining_file="$(mktemp)"
deleted=0
failed=0
i=0
while IFS= read -r id; do
  [ -n "$id" ] || continue
  i=$((i + 1))

  code=$(curl -sS -o /dev/null -w '%{http_code}' -X DELETE "${BASE_URL}/node/${id}" \
    -H "accept: application/json" \
    -H "Authorization: Bearer ${TOKEN}")

  # 200 — удалили, 404 — ноды уже нет (считаем успехом)
  if [ "$code" = "200" ] || [ "$code" = "204" ] || [ "$code" = "404" ]; then
    deleted=$((deleted + 1))
  else
    echo "  [id=$id] ошибка HTTP $code — оставляю в файле"
    echo "$id" >> "$remaining_file"
    failed=$((failed + 1))
  fi

  if [ $((i % 25)) -eq 0 ]; then
    echo "  ...прогресс: $i/$total (удалено $deleted, ошибок $failed)"
  fi
done < "$IDS_FILE"

mv "$remaining_file" "$IDS_FILE"
echo "Готово. Удалено: $deleted, ошибок: $failed. Остаток id в $IDS_FILE"
