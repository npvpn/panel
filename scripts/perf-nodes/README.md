# perf-nodes — нагрузочная проверка вкладки хостов (NPVPN-1585)

Вспомогательные скрипты, чтобы наплодить много нод на стейдже и проверить,
что вкладка хостов открывается быстро (после фикса ленивого рендера попапа нод).

## Как пользоваться

Задать базу API (без хардкода в скриптах — репозиторий публичный):

```bash
export BASE_URL='https://<panel-host>/api'
```

Получить Bearer-токен админа панели:

```bash
curl -X GET "$BASE_URL/admin" \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <token>'
```

Создать 200 нод (id пишутся в `created_node_ids.txt`):

```bash
TOKEN="<bearer>" ./create_nodes.sh 200
```

Удалить всё созданное (читает `created_node_ids.txt`):

```bash
TOKEN="<bearer>" ./delete_nodes.sh
```

## Детали

- Ноды создаются с `add_as_new_host=false` — хосты не плодятся, только ноды.
- Адреса фейковые (`240.0.0.x`), ноды повиснут в `connecting`/`error` —
  для проверки рендера списка нод это неважно.
- `delete_nodes.sh` вычёркивает удалённые id из файла, поэтому его можно
  перезапускать — останутся только неудалённые.

Переменные окружения (обе команды): `BASE_URL` (default `https://rutest.npvpn.net/api`),
`IDS_FILE` (default `created_node_ids.txt`). Для `create_nodes.sh` дополнительно:
`PREFIX`, `RUN`, `COUNT`.
