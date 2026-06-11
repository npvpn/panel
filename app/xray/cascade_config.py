"""Чистая генерация каскадной части конфига под роль ноды (NPVPN-1472).

Без тяжёлых импортов (app.db, config, xray_api), чтобы покрываться pytest без БД.
Все builder'ы возвращают новые dict'ы; cascade_config копирует входной конфиг
(base_config.copy() → deepcopy у XRayConfig) и не мутирует оригинал.
"""
from __future__ import annotations

CASCADE_INBOUND_TAG = "CASCADE_IN"


def cascade_outbound_tag(exit_node_id: int) -> str:
    return f"CASCADE_OUT_{exit_node_id}"


def build_receiving_inbound(exit_params: dict) -> dict:
    """Принимающий vless+TCP+REALITY инбаунд на выходной ноде.

    Структура соответствует проверенному на стейдже inbound'у VLESS TCP REALITY
    (dest+serverNames, xver, fingerprint, sniffing).
    """
    return {
        "tag": CASCADE_INBOUND_TAG,
        "listen": "0.0.0.0",
        "port": exit_params["port"],
        "protocol": "vless",
        "settings": {
            "clients": [{"id": exit_params["uuid"], "flow": "xtls-rprx-vision"}],
            "decryption": "none",
        },
        "streamSettings": {
            "network": "tcp",
            "tcpSettings": {},
            "security": "reality",
            "realitySettings": {
                "show": False,
                "dest": exit_params["dest"],
                "xver": 0,
                "serverNames": [exit_params["sni"]],
                "privateKey": exit_params["private_key"],
                "shortIds": [exit_params["short_id"]],
                "fingerprint": exit_params["fingerprint"],
            },
        },
        "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
    }


def build_cascade_outbound(route: dict) -> dict:
    """vless+TCP+REALITY outbound с входной ноды на принимающий инбаунд выходной.

    Структура соответствует проверенному на стейдже outbound'у OUT_TO_NL_TEST
    (flow vision, encryption none, fingerprint/serverName/publicKey/shortId).
    """
    return {
        "tag": cascade_outbound_tag(route["exit_node_id"]),
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": route["exit_address"],
                "port": route["port"],
                "users": [{
                    "id": route["uuid"],
                    "encryption": "none",
                    "flow": "xtls-rprx-vision",
                }],
            }],
        },
        "streamSettings": {
            "network": "tcp",
            "security": "reality",
            "realitySettings": {
                "show": False,
                "fingerprint": route["fingerprint"],
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
        "outboundTag": cascade_outbound_tag(route["exit_node_id"]),
    }


def cascade_config(base_config, *, role, exit_params=None, entry_routes=None):
    """Добавить каскадную часть конфига по роли ноды.

    role="exit"  → добавить принимающий cascade-инбаунд (exit_params).
    role="entry" → на каждую route добавить outbound (dedup по выходной) + routing-правило.
    role="direct"/нет данных → вернуть base_config без изменений (обратная совместимость).
    Базовые inbounds/outbounds/routing сохраняются — каскад только добавляется.
    """
    if role == "exit" and exit_params:
        cfg = base_config.copy()
        cfg["inbounds"] = cfg["inbounds"] + [build_receiving_inbound(exit_params)]
        return cfg

    if role == "entry" and entry_routes:
        cfg = base_config.copy()
        seen_outbounds = set()
        for route in entry_routes:
            tag = cascade_outbound_tag(route["exit_node_id"])
            if tag not in seen_outbounds:
                cfg["outbounds"] = cfg["outbounds"] + [build_cascade_outbound(route)]
                seen_outbounds.add(tag)
            routing = cfg.setdefault("routing", {})
            routing["rules"] = routing.get("rules", []) + [build_routing_rule(route)]
        return cfg

    return base_config
