# Стандарт логирования панели

Документ описывает архитектуру логирования, env-переменные и правила для нового кода.
Написан для Фазы 0 (tooling), обязателен к соблюдению в последующих фазах (xray, джобы, Celery).

---

## 1. Архитектура

Конфигурация строится при старте:

```python
# app/__init__.py → on_startup()
settings = LogSettings.from_env(os.environ)
logging.config.dictConfig(build_logging_config(settings))
```

`_setup_file_logging()` вызывается **после** того как uvicorn сконфигурировал свои логгеры —
иначе наш `dictConfig` будет перезаписан uvicorn'ом.

### Логгеры

| Логгер | Хендлеры | Примечание |
|---|---|---|
| `uvicorn.error` | console + file | uvicorn-события, ошибки сервера |
| `uvicorn.access` | access | HTTP access-лог; управляется `LOG_ACCESS_ENABLED` |
| `app` (и `app.*`) | console + file | **весь наш код** — использовать только эти логгеры |
| root | console + file | fallback для сторонних библиотек |

---

## 2. Хендлеры и разделение

| Хендлер | Класс | Назначение |
|---|---|---|
| `console` | `logging.StreamHandler` | stdout/stderr (docker logs) |
| `file` | `RotatingFileHandler` | `{LOG_DIR}/marzban.log`, ротация по размеру |
| `access` | `logging.StreamHandler` | HTTP access-лог с фильтром шума |

`file`-хендлер пишет в `{LOG_DIR}/marzban.log` (по умолчанию `/var/log/app/marzban.log`).
Ротация: максимальный размер файла — `LOG_FILE_MAX_SIZE_MB` МБ, число резервных копий — `LOG_FILE_BACKUP_COUNT`.

Access-логгер (`uvicorn.access`) намеренно отделён: это позволяет подавлять шумные
health-check/metrics-запросы не затрагивая основной лог.

---

## 3. Env-переменные

Все параметры управляются из окружения **без правки кода**.

| Переменная | Дефолт | Назначение |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Уровень логирования (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `LOG_FORMAT` | `text` | Формат: `text` — читаемая строка, `json` — структурированный JSON |
| `LOG_DIR` | `/var/log/app` | Директория для файлового лога |
| `LOG_FILE_MAX_SIZE_MB` | `50` | Максимальный размер файла лога в МБ (RotatingFileHandler) |
| `LOG_FILE_BACKUP_COUNT` | `10` | Количество резервных копий при ротации |
| `LOG_ACCESS_ENABLED` | `true` | Включить/выключить HTTP access-лог (`uvicorn.access`) |
| `LOG_ACCESS_NOISE_PATHS` | `/metrics` | Пути через запятую, которые глушатся в access-логе (успешные запросы) |
| `LOG_SQL_SLOW_ENABLED` | `true` | Включить лог медленных SQL-запросов |

Пример `.env`:

```
LOG_LEVEL=DEBUG
LOG_FORMAT=json
LOG_DIR=/var/log/app
LOG_FILE_MAX_SIZE_MB=100
LOG_FILE_BACKUP_COUNT=5
LOG_ACCESS_ENABLED=true
LOG_ACCESS_NOISE_PATHS=/metrics,/health
LOG_SQL_SLOW_ENABLED=true
```

---

## 4. Контекстные поля (rid / node_id / user_id)

Модуль `app/logging_context.py` позволяет добавить в каждую строку лога идентификаторы
текущего запроса/операции через `contextvars` (безопасно в async-коде).

```python
from app.logging_context import set_log_context, clear_log_context

set_log_context(rid="abc123", node_id=42, user_id=7)
# ... весь последующий код в этом async-контексте получит поля в логах ...
clear_log_context()
```

В text-формате они появляются как:

```
2025-01-01 12:00:00 INFO     app.xray [rid=abc123 node=42 user=7] Операция завершена
```

В JSON-формате — отдельными полями `rid`, `node_id`, `user_id`.

Если контекст не установлен — поля выводятся как `-`.

**Когда устанавливать контекст:**
- Xray-операции — установить `node_id` (и `rid`, если есть цепочка запроса).
- Джобы — установить идентификатор джобы в `rid`.
- HTTP middleware — устанавливает `rid` из заголовка `X-Request-ID` (или генерирует `uuid4().hex`).

---

## 5. Подавление шума (AccessNoiseFilter)

`AccessNoiseFilter` применяется к хендлеру `access`.

Логика:
- Если путь запроса содержит один из `LOG_ACCESS_NOISE_PATHS` **и** статус не 4xx/5xx — запись **подавляется**.
- Ошибки (любые записи, содержащие ` 4` или ` 5` в сообщении) **не подавляются** независимо от пути.

Пример: `/metrics` вызывается Prometheus каждые 15 с, но успешные 200-ответы не попадают
в access-лог. Если `/metrics` вернёт 503 — запись будет видна.

---

## 6. JSON-формат

При `LOG_FORMAT=json` используется `JsonFormatter` из `app/logging_config.py`.

Поля JSON-записи:

| Поле | Источник |
|---|---|
| `ts` | `record.asctime` |
| `level` | `record.levelname` |
| `logger` | `record.name` |
| `rid` | контекст (`-` если не задан) |
| `node_id` | контекст (`-` если не задан) |
| `user_id` | контекст (`-` если не задан) |
| `msg` | `record.getMessage()` |

JSON-формат удобен для парсинга в Loki/Grafana.

---

## 7. Стандарт для нового кода

Это требования к коду всех последующих фаз (xray, джобы, Celery и т.д.).

### Использовать именованные логгеры

```python
import logging

logger = logging.getLogger("app.<подмодуль>")
# Примеры:
# logging.getLogger("app.xray")
# logging.getLogger("app.jobs.review")
# logging.getLogger("app.routers.node")
```

**Нельзя:**
- `logging.getLogger()` (root-логгер без имени) — теряется информация об источнике.
- `print()` — не попадает в файловый лог и не фильтруется.

### Устанавливать контекст там, где он есть

```python
from app.logging_context import set_log_context, clear_log_context

# В xray-операции:
set_log_context(node_id=node.id)
try:
    ...
finally:
    clear_log_context()
```

### Уровни — осмысленно

| Уровень | Когда использовать |
|---|---|
| `DEBUG` | Детали реализации, промежуточные значения, диагностика |
| `INFO` | Бизнес-события: пользователь создан, подписка активирована, нода добавлена |
| `WARNING` | Неожиданная ситуация, из которой система восстановилась |
| `ERROR` | Ошибка, которую нужно расследовать |
| `CRITICAL` | Критический сбой, система не может продолжать |

**Не плодить мусорные per-request INFO** — один успешный HTTP-запрос не должен порождать
несколько INFO-строк в основном логе (для этого есть access-лог).

### Структура сообщений

Используй аргументы `%s`-форматирования, не f-строки в вызове логгера:

```python
# Правильно:
logger.info("Node %s connected, inbounds=%d", node.id, len(inbounds))

# Неправильно (форматирование происходит даже если уровень выключен):
logger.info(f"Node {node.id} connected, inbounds={len(inbounds)}")
```

Для структурированного контекста — используй именованные поля через `extra` или `set_log_context`,
а не вставку значений в строку сообщения.
