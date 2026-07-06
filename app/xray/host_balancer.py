"""Чистая генерация xray-балансировщика для multi-address хостов подписки (NPVPN-1596).

Хост, связанный с несколькими нодами (или со статическим address через запятую),
в формате v2ray-json отдаётся одним конфигом с N proxy-outbound (теги proxy, proxy-1, …)
и балансировщиком strategy=random. Мёртвые ноды отсеиваются observatory: RandomStrategy
в xray-core фильтрует кандидатов по observation, если observatory присутствует.

Без импортов БД/шаблонов — покрывается pytest без окружения (как cascade_config/bs_routing).
"""

from __future__ import annotations

PROXY_OUTBOUND_TAG = "proxy"
HOST_BALANCER_TAG = "proxy-balancer"
HOST_BALANCER_STRATEGY = "random"

OBSERVATORY_PROBE_URL = "https://www.google.com/generate_204"
OBSERVATORY_INTERVAL = "1m"


def proxy_outbound_tag(index: int) -> str:
    """Тег proxy-outbound: первый — 'proxy' (обратная совместимость с явным
    outboundTag:'proxy' в пользовательском routing), остальные — 'proxy-<i>'."""
    return PROXY_OUTBOUND_TAG if index == 0 else f"{PROXY_OUTBOUND_TAG}-{index}"


def build_balancer() -> dict:
    """Балансировщик по всем proxy-outbound (селектор по префиксу тега)."""
    return {
        "tag": HOST_BALANCER_TAG,
        "selector": [PROXY_OUTBOUND_TAG],
        "strategy": {"type": HOST_BALANCER_STRATEGY},
    }


def build_balancer_rule() -> dict:
    """Catch-all: весь оставшийся tcp/udp-трафик → балансировщик.

    Ставится ПОСЛЕДНИМ в rules — xray матчит сверху вниз, first-match-wins, так что
    правила block/direct должны отработать раньше. Раньше этот трафик уходил в первый
    outbound (proxy) как дефолт xray; теперь его перехватывает balancerTag."""
    return {
        "type": "field",
        "network": "tcp,udp",
        "balancerTag": HOST_BALANCER_TAG,
    }


def build_observatory() -> dict:
    """Health-check proxy-outbound'ов: по нему random отсеивает мёртвые ноды."""
    return {
        "subjectSelector": [PROXY_OUTBOUND_TAG],
        "probeUrl": OBSERVATORY_PROBE_URL,
        "probeInterval": OBSERVATORY_INTERVAL,
    }


def apply_host_balancer(config: dict) -> dict:
    """Дописать в собранный v2ray-json конфиг балансировщик, catch-all rule и observatory.

    Вызывается только когда proxy-outbound'ов >1 (см. V2rayJsonConfig.add_balanced).
    Мутирует и возвращает config.
    """
    routing = config.setdefault("routing", {})
    routing["balancers"] = routing.get("balancers", []) + [build_balancer()]
    routing["rules"] = routing.get("rules", []) + [build_balancer_rule()]
    config["observatory"] = build_observatory()
    return config
