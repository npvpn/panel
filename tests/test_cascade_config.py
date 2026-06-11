import copy

from app.xray.cascade_config import (
    CASCADE_INBOUND_TAG,
    cascade_config,
    cascade_outbound_tag,
)


class FakeConfig(dict):
    """Имитирует XRayConfig: .copy() делает deepcopy (как в app/xray/config.py)."""

    def copy(self):
        return FakeConfig(copy.deepcopy(dict(self)))


def base():
    return FakeConfig({
        "inbounds": [{"tag": "VLESS_TCP", "protocol": "vless"}],
        "outbounds": [{"protocol": "freedom", "tag": "DIRECT"},
                      {"protocol": "blackhole", "tag": "BLOCK"}],
        "routing": {"rules": [{"ip": ["geoip:private"], "outboundTag": "BLOCK", "type": "field"}]},
    })


EXIT_PARAMS = {
    "port": 2096, "uuid": "uuid-1",
    "private_key": "PRIV", "public_key": "PUB",
    "short_id": "abcd1234", "sni": "xapi.ozon.ru", "dest": "xapi.ozon.ru:443",
    "fingerprint": "chrome",
}


def route(exit_id=7, inbound="VLESS_TCP"):
    return {
        "entry_inbound_tag": inbound, "exit_node_id": exit_id, "exit_address": "10.0.0.2",
        "port": 2096, "uuid": "uuid-1", "public_key": "PUB", "short_id": "abcd1234",
        "sni": "xapi.ozon.ru", "fingerprint": "chrome",
    }


def test_direct_role_returns_config_unchanged():
    cfg = base()
    assert cascade_config(cfg, role="direct") is cfg


def test_exit_role_appends_receiving_inbound():
    result = cascade_config(base(), role="exit", exit_params=EXIT_PARAMS)
    tags = [i["tag"] for i in result["inbounds"]]
    assert tags == ["VLESS_TCP", CASCADE_INBOUND_TAG]
    cin = result["inbounds"][-1]
    assert cin["port"] == 2096
    assert cin["settings"]["clients"][0]["id"] == "uuid-1"
    assert cin["streamSettings"]["realitySettings"]["privateKey"] == "PRIV"


def test_exit_role_keeps_user_inbounds_legacy():
    # exit + легаси: пользовательский инбаунд не вытесняется ролью.
    result = cascade_config(base(), role="exit", exit_params=EXIT_PARAMS)
    assert {"tag": "VLESS_TCP", "protocol": "vless"} in result["inbounds"]


def test_entry_role_adds_outbound_and_rule():
    result = cascade_config(base(), role="entry", entry_routes=[route(exit_id=7)])
    out_tags = [o["tag"] for o in result["outbounds"]]
    assert out_tags == ["DIRECT", "BLOCK", cascade_outbound_tag(7)]
    out = result["outbounds"][-1]
    assert out["settings"]["vnext"][0]["address"] == "10.0.0.2"
    assert out["settings"]["vnext"][0]["users"][0]["flow"] == "xtls-rprx-vision"
    assert out["streamSettings"]["realitySettings"]["publicKey"] == "PUB"
    assert out["streamSettings"]["realitySettings"]["fingerprint"] == "chrome"
    rule = result["routing"]["rules"][-1]
    assert rule == {"type": "field", "inboundTag": ["VLESS_TCP"],
                    "outboundTag": cascade_outbound_tag(7)}


def test_entry_role_dedupes_outbound_per_exit():
    # две route на один exit (разные инбаунды) → один outbound, два routing-правила.
    routes = [route(exit_id=7, inbound="VLESS_TCP"), route(exit_id=7, inbound="VMESS_WS")]
    result = cascade_config(base(), role="entry", entry_routes=routes)
    out_tags = [o["tag"] for o in result["outbounds"]]
    assert out_tags.count(cascade_outbound_tag(7)) == 1
    cascade_rules = [r for r in result["routing"]["rules"]
                     if r.get("outboundTag") == cascade_outbound_tag(7)]
    assert len(cascade_rules) == 2


def test_does_not_mutate_input():
    cfg = base()
    snapshot = copy.deepcopy(dict(cfg))
    cascade_config(cfg, role="entry", entry_routes=[route()])
    cascade_config(cfg, role="exit", exit_params=EXIT_PARAMS)
    assert dict(cfg) == snapshot
