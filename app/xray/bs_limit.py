"""Чистые функции для по-нодного лимита БС-нод (NPVPN-1456).

Без зависимостей от БД/окружения — тестируются как cascade_config/inbound_filter.
"""


def period_keys(now):
    """(день 'YYYY-MM-DD', месяц 'YYYY-MM') — маркеры периода счётчика."""
    return now.strftime("%Y-%m-%d"), now.strftime("%Y-%m")


def bs_counter_step(existing, delta, today, yyyymm):
    """Новые значения счётчика с ленивым сбросом периодов.

    existing — dict с ключами daily_used/daily_period/monthly_used/monthly_period
    либо None (строки ещё нет). Возвращает dict с теми же ключами.
    """
    existing = existing or {}
    daily_base = existing.get("daily_used", 0) if existing.get("daily_period") == today else 0
    monthly_base = existing.get("monthly_used", 0) if existing.get("monthly_period") == yyyymm else 0
    return {
        "daily_used": daily_base + delta,
        "daily_period": today,
        "monthly_used": monthly_base + delta,
        "monthly_period": yyyymm,
    }


def diff_blocks(desired, current):
    """desired/current — множества (node_id, user_id). → (to_block, to_unblock)."""
    return desired - current, current - desired


def strip_blocked_clients(config, blocked_user_ids):
    """Копия config без клиентов заблокированных user_id во всех инбаундах.

    Матчинг по префиксу email '<uid>.' (email клиента = '<user_id>.<username>').
    Пустой набор → исходный объект без копирования (no-op). Затронутые инбаунды
    пересобираются новыми dict, поэтому функция корректна даже при поверхностном
    config.copy() и не мутирует вход.
    """
    if not blocked_user_ids:
        return config
    cfg = config.copy()
    prefixes = tuple(f"{uid}." for uid in blocked_user_ids)
    new_inbounds = []
    for inbound in cfg["inbounds"]:
        settings = inbound.get("settings")
        clients = settings.get("clients") if settings else None
        if not clients:
            new_inbounds.append(inbound)
            continue
        new_settings = dict(settings)
        new_settings["clients"] = [
            c for c in clients
            if not str(c.get("email", "")).startswith(prefixes)
        ]
        new_inbound = dict(inbound)
        new_inbound["settings"] = new_settings
        new_inbounds.append(new_inbound)
    cfg["inbounds"] = new_inbounds
    return cfg
