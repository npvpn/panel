#!/usr/bin/env bash
#
# NPVPN-1585 — создание фейковых нод для нагрузочной проверки вкладки хостов.
#
# Создаёт COUNT нод через POST /api/node и пишет их id в IDS_FILE,
# чтобы потом удалить скриптом delete_nodes.sh.
#
# Ноды создаются с add_as_new_host=false — хосты НЕ плодятся, только ноды.
# Адреса фейковые (240.0.0.x), ноды повиснут в статусе connecting/error —
# для проверки рендера списка нод это неважно.
#
# Использование:
#   TOKEN="<bearer>" ./create_nodes.sh [COUNT]
#
# Переменные окружения:
#   TOKEN     — Bearer-токен админа (ОБЯЗАТЕЛЬНО). Получить:
#                 curl -X GET '<BASE_URL>/admin' \
#                   -H 'Authorization: Bearer <token>'
#   BASE_URL  — база API, напр. https://<panel-host>/api (ОБЯЗАТЕЛЬНО)
#   PREFIX    — префикс имени ноды (default: perftest-1585)
#   RUN       — метка прогона в имени (default: текущее время)
#   IDS_FILE  — файл со списком созданных id (default: created_node_ids.txt)
#   COUNT     — сколько нод создать (можно 1-м аргументом, default: 200)
#
set -uo pipefail

: "${TOKEN:?Задай TOKEN='<bearer>' — токен админа панели}"
: "${BASE_URL:?Задай BASE_URL='https://<panel-host>/api'}"
PREFIX="${PREFIX:-perftest-1585}"
RUN="${RUN:-$(date +%Y%m%d-%H%M%S)}"
IDS_FILE="${IDS_FILE:-created_node_ids.txt}"
COUNT="${1:-${COUNT:-200}}"

command -v jq >/dev/null 2>&1 || { echo "Нужен jq"; exit 1; }

echo "Создаю $COUNT нод на $BASE_URL (префикс: ${PREFIX}-${RUN})"
echo "id пишу в: $IDS_FILE"
: > "$IDS_FILE"

created=0
failed=0
for i in $(seq 1 "$COUNT"); do
  name="${PREFIX}-${RUN}-$(printf '%03d' "$i")"
  addr="240.0.$(( (i >> 8) & 255 )).$(( i & 255 ))"

  resp=$(curl -sS -w $'\n%{http_code}' -X POST "${BASE_URL}/node" \
    -H "accept: application/json" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"${name}\",\"address\":\"${addr}\",\"port\":62050,\"api_port\":62051,\"protocol\":\"rest\",\"usage_coefficient\":1,\"add_as_new_host\":false}")

  code=$(printf '%s' "$resp" | tail -n1)
  body=$(printf '%s' "$resp" | sed '$d')

  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    id=$(printf '%s' "$body" | jq -r '.id // empty')
    if [ -n "$id" ]; then
      echo "$id" >> "$IDS_FILE"
      created=$((created + 1))
    else
      echo "  [$i] 200, но нет id в ответе: $body"
      failed=$((failed + 1))
    fi
  else
    echo "  [$i] ошибка HTTP $code: $(printf '%s' "$body" | head -c 200)"
    failed=$((failed + 1))
  fi

  if [ $((i % 25)) -eq 0 ]; then
    echo "  ...прогресс: $i/$COUNT (создано $created, ошибок $failed)"
  fi
done

echo "Готово. Создано: $created, ошибок: $failed. id в $IDS_FILE"
