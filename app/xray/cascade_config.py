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

    Параметры REALITY (publicKey/shortId/serverName/fingerprint) и port уже разрешены в
    operations.py из определения cascade-инбаунда; fingerprint фоллбэчится на CASCADE_FINGERPRINT.
    """
    return {
        "tag": cascade_outbound_tag(route["exit_node_id"], route["cascade_inbound_tag"]),
        "protocol": "vless",
        "settings": {
            "vnext": [
                {
                    "address": route["address"],
                    "port": route["port"],
                    "users": [
                        {
                            "id": route["uuid"],
                            "encryption": "none",
                            "flow": CASCADE_CLIENT_FLOW,
                        }
                    ],
                }
            ],
        },
        "streamSettings": {
            "network": "tcp",
            "security": "reality",
            "realitySettings": {
                "show": False,
                "fingerprint": route.get("fingerprint") or CASCADE_FINGERPRINT,
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


BALANCER_STRATEGIES = ("random", "roundRobin", "leastPing", "leastLoad")
OBSERVATORY_PROBE_URL = "https://www.google.com/generate_204"
OBSERVATORY_INTERVAL = "10s"
CASCADE_OUTBOUND_PREFIX = "CASCADE_OUT_"


def cascade_balancer_tag(entry_inbound_tag: str) -> str:
    return f"CASCADE_BAL_{entry_inbound_tag}"


def build_balancer(balancer_tag: str, selector: list, strategy: str) -> dict:
    """Балансировщик xray по группе cascade-outbound'ов одного входного инбаунда."""
    strategy_type = strategy if strategy in BALANCER_STRATEGIES else "random"
    return {
        "tag": balancer_tag,
        "selector": selector,
        "strategy": {"type": strategy_type},
    }


def build_balancer_rule(entry_inbound_tag: str, balancer_tag: str) -> dict:
    return {
        "type": "field",
        "inboundTag": [entry_inbound_tag],
        "balancerTag": balancer_tag,
    }


def build_observatory() -> dict:
    return {
        "subjectSelector": [CASCADE_OUTBOUND_PREFIX],
        "probeUrl": OBSERVATORY_PROBE_URL,
        "probeInterval": OBSERVATORY_INTERVAL,
    }


def build_burst_observatory() -> dict:
    return {
        "subjectSelector": [CASCADE_OUTBOUND_PREFIX],
        "pingConfig": {
            "destination": OBSERVATORY_PROBE_URL,
            "interval": OBSERVATORY_INTERVAL,
            "connectivity": "",
            "timeout": "3s",
            "sampling": 3,
        },
    }


def cascade_config(base_config, *, role, cascade_clients=None, entry_routes=None, strategy="random"):
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
            _inject_cascade_client(ib, uuid_by_tag[ib.get("tag")]) if ib.get("tag") in uuid_by_tag else ib
            for ib in cfg["inbounds"]
        ]
        return cfg

    if role == "entry" and entry_routes:
        cfg = base_config.copy()

        # 1) outbounds: по одному на (exit, cascade_inbound), dedup по тегу.
        seen_outbounds = set()
        for route in entry_routes:
            tag = cascade_outbound_tag(route["exit_node_id"], route["cascade_inbound_tag"])
            if tag not in seen_outbounds:
                cfg["outbounds"] = cfg["outbounds"] + [build_cascade_outbound(route)]
                seen_outbounds.add(tag)

        # 2) группировка route'ов по entry_inbound_tag (сохраняя порядок появления).
        groups = {}
        for route in entry_routes:
            groups.setdefault(route["entry_inbound_tag"], []).append(route)

        routing = cfg.setdefault("routing", {})
        has_balancer = False
        for entry_tag, group in groups.items():
            # уникальные outbound-теги группы, сохраняя порядок.
            selector = []
            for route in group:
                out_tag = cascade_outbound_tag(route["exit_node_id"], route["cascade_inbound_tag"])
                if out_tag not in selector:
                    selector.append(out_tag)

            if len(selector) > 1:
                bal_tag = cascade_balancer_tag(entry_tag)
                routing["balancers"] = routing.get("balancers", []) + [build_balancer(bal_tag, selector, strategy)]
                # Cascade routing rules are appended AFTER any pre-existing base rules.
                # xray matches rules top-to-bottom, first match wins — so the base config
                # must not carry an earlier rule matching a cascade entry_inbound_tag,
                # or this appended balancer/outbound rule would never be reached.
                routing["rules"] = routing.get("rules", []) + [build_balancer_rule(entry_tag, bal_tag)]
                has_balancer = True
            else:
                # одиночный exit на инбаунд — прежнее поведение.
                # Same append-after invariant applies (see comment above).
                routing["rules"] = routing.get("rules", []) + [build_routing_rule(group[0])]

        # 3) observatory только для ping/load-стратегий и только если есть балансировщики.
        if has_balancer:
            if strategy == "leastPing":
                cfg["observatory"] = build_observatory()
                # subjectSelector prefix "CASCADE_OUT_" intentionally covers ALL cascade
                # outbounds on the node, including single-exit (non-balanced) ones —
                # accepted as harmless over-probing for v1.
            elif strategy == "leastLoad":
                cfg["burstObservatory"] = build_burst_observatory()
                # Same intentional over-probing rationale as observatory above.

        return cfg

    return base_config
