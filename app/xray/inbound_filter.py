"""Чистая логика фильтрации инбаундов конфига под конкретную ноду.

Вынесено в отдельный модуль без тяжёлых импортов (app.db, config, xray_api),
чтобы покрывалось pytest без поднятия БД/окружения.
"""

from __future__ import annotations

from collections.abc import Iterable


def filtered_inbounds(
    inbounds: list[dict],
    managed_tags: Iterable[str],
    allowed_tags: Iterable[str],
) -> list[dict]:
    """Вернуть подсписок inbounds, оставив:

    - все инфраструктурные инбаунды (tag НЕ входит в managed_tags), напр. API_INBOUND,
      fallback- и excluded-инбаунды — они нужны всегда;
    - управляемые прокси-инбаунды, чей tag входит в allowed_tags.

    Порядок исходного списка сохраняется. Исходный список не мутируется
    (элементы возвращаются по ссылке — вызывающий код их не меняет).
    """
    managed = set(managed_tags)
    allowed = set(allowed_tags)
    return [inbound for inbound in inbounds if inbound["tag"] not in managed or inbound["tag"] in allowed]


def apply_inbound_filter(base_config, allowed_tags):
    """Config-level фильтр инбаундов (общий для нод и главного core).

    allowed_tags пуст/None → base_config без изменений (обратная совместимость:
    поднимаются все инбаунды). Иначе — base_config.copy() с оставленными
    инфраструктурными инбаундами и разрешёнными управляемыми (allowed_tags).
    """
    if not allowed_tags:
        return base_config
    cfg = base_config.copy()
    cfg["inbounds"] = filtered_inbounds(
        cfg["inbounds"],
        managed_tags=set(base_config.inbounds_by_tag.keys()),
        allowed_tags=set(allowed_tags),
    )
    return cfg
