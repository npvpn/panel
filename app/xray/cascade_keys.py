"""Служебная личность выходной ноды для каскада (NPVPN-1472 v2).

Раньше тут генерился весь служебный инбаунд (порт + REALITY keypair). Теперь приёмник —
каталожный инбаунд из xray_config.json, и от выходной нужен только устойчивый uuid
служебного cascade-клиента, который инъектится в выбранный инбаунд. publicKey для outbound
деривится из privateKey инбаунда в operations.py (через app.xray.core.get_x25519).
"""

from __future__ import annotations

from uuid import uuid4


def generate_cascade_identity(*, uuid_str: str | None = None) -> dict:
    """Собрать содержимое Node.cascade_params: {"uuid": ...}."""
    return {"uuid": uuid_str or str(uuid4())}
