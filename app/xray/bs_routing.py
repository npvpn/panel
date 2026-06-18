"""Чистые функции выбора клиентского routing для БС/не-БС нод (NPVPN-1494).

Без зависимостей от БД/окружения — тестируются как bs_limit/inbound_filter.
"""
import json
from typing import Optional


def parse_json_object(raw: Optional[str]) -> Optional[dict]:
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
    routing_default: Optional[dict],
    routing_bs: Optional[dict],
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
