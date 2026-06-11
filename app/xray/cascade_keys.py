"""Генерация credentials для каскадного cascade-инбаунда выходной ноды (NPVPN-1472).

REALITY-keypair берётся через бинарь xray (app.xray.core.get_x25519) — импорт ленивый,
чтобы модуль оставался импортируемым в bare-pytest (keypair инжектится в тестах).
"""
from __future__ import annotations

import secrets
from uuid import uuid4

CASCADE_INBOUND_PORT = 2096
CASCADE_DEFAULT_SNI = "xapi.ozon.ru"  # проверено на стейдже
CASCADE_DEFAULT_FINGERPRINT = "chrome"


def generate_cascade_params(
    *,
    port: int = CASCADE_INBOUND_PORT,
    sni: str = CASCADE_DEFAULT_SNI,
    fingerprint: str = CASCADE_DEFAULT_FINGERPRINT,
    keypair: dict | None = None,
    uuid_str: str | None = None,
    short_id: str | None = None,
) -> dict:
    """Собрать dict cascade-параметров для Node.cascade_params.

    keypair=None → сгенерировать через xray x25519 (требует бинарь, прод-путь).
    uuid_str/short_id=None → сгенерировать случайные.
    """
    if keypair is None:
        from app import xray
        keypair = xray.core.get_x25519()
    return {
        "port": port,
        "uuid": uuid_str or str(uuid4()),
        "private_key": keypair["private_key"],
        "public_key": keypair["public_key"],
        "short_id": short_id or secrets.token_hex(8),
        "sni": sni,
        "dest": f"{sni}:443",
        "fingerprint": fingerprint,
    }
