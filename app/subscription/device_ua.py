"""Сопоставление User-Agent для unknown-устройств без hwid.

Без зависимостей от БД/окружения — тестируется как bs_limit/inbound_filter.
"""


def unknown_user_agents_match(stored: str | None, incoming: str | None) -> bool:
    def norm(v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s if s else None

    stored_n = norm(stored)
    incoming_n = norm(incoming)
    # Legacy unknown devices were saved with placeholder/empty UA before UA checks existed.
    if stored_n in (None, "Неизвестно"):
        return True
    if incoming_n is None:
        return False
    return stored_n == incoming_n
