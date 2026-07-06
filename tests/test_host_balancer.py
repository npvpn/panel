"""Чистые билдеры xray-балансировщика для multi-address хостов (NPVPN-1596)."""

from __future__ import annotations

from app.xray.host_balancer import (
    HOST_BALANCER_TAG,
    apply_host_balancer,
    build_balancer,
    build_balancer_rule,
    build_observatory,
    proxy_outbound_tag,
)


def test_proxy_outbound_tag_first_is_plain_proxy():
    assert proxy_outbound_tag(0) == "proxy"


def test_proxy_outbound_tag_rest_are_suffixed():
    assert proxy_outbound_tag(1) == "proxy-1"
    assert proxy_outbound_tag(2) == "proxy-2"


def test_build_balancer_random_over_proxy_prefix():
    bal = build_balancer()
    assert bal["tag"] == HOST_BALANCER_TAG
    assert bal["selector"] == ["proxy"]
    assert bal["strategy"] == {"type": "random"}


def test_build_balancer_rule_is_catch_all_tcp_udp():
    rule = build_balancer_rule()
    assert rule["type"] == "field"
    assert rule["network"] == "tcp,udp"
    assert rule["balancerTag"] == HOST_BALANCER_TAG
    assert "outboundTag" not in rule


def test_build_observatory_probes_proxy_prefix():
    obs = build_observatory()
    assert obs["subjectSelector"] == ["proxy"]
    assert obs["probeUrl"]
    assert obs["probeInterval"]


def test_apply_host_balancer_appends_balancer_and_catch_all_last():
    config = {
        "outbounds": [
            {"tag": "proxy"}, {"tag": "proxy-1"},
            {"tag": "direct"}, {"tag": "block"},
        ],
        "routing": {
            "rules": [
                {"type": "field", "domain": ["geosite:category-ads-all"], "outboundTag": "block"},
                {"type": "field", "ip": ["geoip:ru"], "outboundTag": "direct"},
            ],
        },
    }
    result = apply_host_balancer(config)

    # балансировщик добавлен
    assert result["routing"]["balancers"] == [build_balancer()]
    # catch-all — последним, прежние правила сохранены и раньше
    rules = result["routing"]["rules"]
    assert rules[-1] == build_balancer_rule()
    assert rules[0]["outboundTag"] == "block"
    assert rules[1]["outboundTag"] == "direct"
    # observatory на верхнем уровне
    assert result["observatory"] == build_observatory()


def test_apply_host_balancer_handles_missing_routing():
    config = {"outbounds": [{"tag": "proxy"}, {"tag": "proxy-1"}]}
    result = apply_host_balancer(config)
    assert result["routing"]["balancers"] == [build_balancer()]
    assert result["routing"]["rules"] == [build_balancer_rule()]
    assert result["observatory"] == build_observatory()
