"""Чистая генерация каскадной части конфига под роль ноды (NPVPN-1472 v2).

Связка вход→выход строится поверх обычного VLESS+TCP+REALITY инбаунда из каталога
xray_config.json (а не служебного сгенерённого инбаунда). На выходной — в выбранный
инбаунд дописывается служебный cascade-client; на входной — outbound на этот инбаунд
с параметрами, прочитанными из его определения (резолвинг — в operations.py).

Без тяжёлых импортов (app.db, config, xray_api), чтобы покрываться pytest без БД.
cascade_config копирует входной конфиг (base_config.copy() → deepcopy у XRayConfig)
и не мутирует оригинал.
"""
from __future__ import annotations

CASCADE_CLIENT_FLOW = "xtls-rprx-vision"
CASCADE_FINGERPRINT = "chrome"


def cascade_outbound_tag(exit_node_id: int, cascade_inbound_tag: str) -> str:
    return f"CASCADE_OUT_{exit_node_id}_{cascade_inbound_tag}"


def _inject_cascade_client(inbound: dict, uuid: str) -> dict:
    """Копия инбаунда с дописанным служебным cascade-клиентом (идемпотентно)."""
    new_inbound = dict(inbound)
    settings = dict(new_inbound.get("settings") or {})
    clients = list(settings.get("clients") or [])
    if not any(c.get("id") == uuid for c in clients):
        clients = clients + [{"id": uuid, "flow": CASCADE_CLIENT_FLOW}]
    settings["clients"] = clients
    new_inbound["settings"] = settings
    return new_inbound


def build_cascade_outbound(route: dict) -> dict:
    """vless+TCP+REALITY outbound с входной ноды на каталожный инбаунд выходной.

    Параметры REALITY (publicKey/shortId/serverName) и port уже разрешены в operations.py
    из определения cascade-инбаунда.
    """
    return {
        "tag": cascade_outbound_tag(route["exit_node_id"], route["cascade_inbound_tag"]),
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": route["address"],
                "port": route["port"],
                "users": [{
                    "id": route["uuid"],
                    "encryption": "none",
                    "flow": CASCADE_CLIENT_FLOW,
                }],
            }],
        },
        "streamSettings": {
            "network": "tcp",
            "security": "reality",
            "realitySettings": {
                "show": False,
                "fingerprint": CASCADE_FINGERPRINT,
                "serverName": route["sni"],
                "publicKey": route["public_key"],
                "shortId": route["short_id"],
            },
        },
    }


def build_routing_rule(route: dict) -> dict:
    """Завернуть трафик с entry_inbound_tag в cascade-outbound нужной выходной."""
    return {
        "type": "field",
        "inboundTag": [route["entry_inbound_tag"]],
        "outboundTag": cascade_outbound_tag(route["exit_node_id"], route["cascade_inbound_tag"]),
    }


def cascade_config(base_config, *, role, cascade_clients=None, entry_routes=None):
    """Добавить каскадную часть конфига по роли ноды.

    role="exit"  → в указанные каталожные инбаунды дописать служебный cascade-client.
    role="entry" → на каждую route добавить outbound (dedup по (exit, inbound)) + routing.
    role="direct"/нет данных → вернуть base_config без изменений.
    Базовые inbounds/outbounds/routing сохраняются — каскад только добавляется.
    """
    if role == "exit" and cascade_clients:
        cfg = base_config.copy()
        # Один служебный uuid на выходную ноду (конфиг строится per-node), поэтому
        # дубликат inbound_tag отображается на тот же uuid — first-wins безопасно.
        uuid_by_tag = {}
        for c in cascade_clients:
            uuid_by_tag.setdefault(c["inbound_tag"], c["uuid"])
        cfg["inbounds"] = [
            _inject_cascade_client(ib, uuid_by_tag[ib.get("tag")])
            if ib.get("tag") in uuid_by_tag else ib
            for ib in cfg["inbounds"]
        ]
        return cfg

    if role == "entry" and entry_routes:
        cfg = base_config.copy()
        seen_outbounds = set()
        for route in entry_routes:
            tag = cascade_outbound_tag(route["exit_node_id"], route["cascade_inbound_tag"])
            if tag not in seen_outbounds:
                cfg["outbounds"] = cfg["outbounds"] + [build_cascade_outbound(route)]
                seen_outbounds.add(tag)
            routing = cfg.setdefault("routing", {})
            routing["rules"] = routing.get("rules", []) + [build_routing_rule(route)]
        return cfg

    return base_config
