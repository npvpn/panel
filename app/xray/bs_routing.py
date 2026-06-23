"""Чистые функции выбора клиентского routing для БС/не-БС нод (NPVPN-1494).

Без зависимостей от БД/окружения — тестируются как bs_limit/inbound_filter.
"""

import json


def parse_json_object(raw: str | None) -> dict | None:
    """Распарсить JSON-строку в объект.

    '' / пробелы / None → None (поле не задано, использовать фолбэк).
    Валидный JSON-объект → dict.
    Невалидный JSON или не-объект (массив/строка/число) → ValueError.
    """
    if raw is None or not str(raw).strip():
        return None
    try:
        value = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def select_routing(
    template_routing: dict,
    routing_default: dict | None,
    routing_bs: dict | None,
    is_bs: bool,
) -> dict:
    """Выбрать секцию routing для объекта-конфига одного сервера.

    БС-хост → routing_bs; обычный → routing_default. Если соответствующий
    блок не задан (None) — фолбэк на routing из общего шаблона (текущее
    поведение, без разделения).
    """
    if is_bs:
        return routing_bs if routing_bs is not None else template_routing
    return routing_default if routing_default is not None else template_routing
