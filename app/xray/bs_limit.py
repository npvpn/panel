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


def aggregate_bs_usage(rows, today, yyyymm):
    """rows: iterable of dict(user_id, daily_used, daily_period, monthly_used, monthly_period).
    → {user_id: {"daily_used", "monthly_used"}}, считая только актуальные периоды."""
    totals = {}
    for r in rows:
        uid = r["user_id"]
        t = totals.setdefault(uid, {"daily_used": 0, "monthly_used": 0})
        if r.get("daily_period") == today:
            t["daily_used"] += r.get("daily_used") or 0
        if r.get("monthly_period") == yyyymm:
            t["monthly_used"] += r.get("monthly_used") or 0
    return totals


def over_limit(daily_used, monthly_used, daily_limit, monthly_limit):
    """True, если превышен любой ЗАДАННЫЙ (>0) лимит. 0/None = лимит не задан."""
    if daily_limit and daily_used >= daily_limit:
        return True
    if monthly_limit and monthly_used >= monthly_limit:
        return True
    return False


def pick_bs_bar(daily_used, daily_limit, monthly_used, monthly_limit):
    """(used, total) для лимита с меньшим остатком; None, если ни один не задан."""
    candidates = []
    if daily_limit:
        candidates.append((daily_limit - daily_used, daily_used, daily_limit))
    if monthly_limit:
        candidates.append((monthly_limit - monthly_used, monthly_used, monthly_limit))
    if not candidates:
        return None
    _, used, total = min(candidates, key=lambda c: c[0])
    return used, total


def bs_stub_remark(text_list):
    """Имя сервера-заглушки БС-лимита из настройки sub_bs_limit_server_text.

    БС-хост заменяется заглушкой НА СВОЁМ МЕСТЕ (один хост → одна заглушка),
    поэтому многострочный текст склеивается в одно имя сервера. Пустые строки
    отбрасываются. Принимает список строк, одну строку или None.
    """
    if not text_list:
        return ""
    lines = [text_list] if isinstance(text_list, str) else list(text_list)
    parts = [str(x).strip() for x in lines]
    return " ".join(p for p in parts if p)


def host_matches_blocked(host_addresses, blocked_addresses):
    """True, если хост указывает на заблокированную БС-ноду (матч по адресу).

    В Marzban инбаунд-теги общие для всех нод, поэтому БС-ноду в подписке
    отличает только адрес хоста (= Node.address). host_addresses — список
    адресов хоста (xray.hosts[tag][i]["address"]). При блоке юзер теряет ноду
    целиком, значит глушим ВСЕ хосты с её адресом, независимо от тега.
    """
    if not blocked_addresses:
        return False
    return any(a in blocked_addresses for a in (host_addresses or []))


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
