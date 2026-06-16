import copy

from app.xray.cascade_config import (
    cascade_config,
    cascade_outbound_tag,
)


class FakeConfig(dict):
    """Имитирует XRayConfig: .copy() делает deepcopy (как в app/xray/config.py)."""

    def copy(self):
        return FakeConfig(copy.deepcopy(dict(self)))


def base():
    return FakeConfig({
        "inbounds": [
            {"tag": "VLESS_TCP", "protocol": "vless",
             "settings": {"clients": [{"id": "user-1"}], "decryption": "none"}},
            {"tag": "OTHER", "protocol": "vless", "settings": {"clients": []}},
        ],
        "outbounds": [{"protocol": "freedom", "tag": "DIRECT"},
                      {"protocol": "blackhole", "tag": "BLOCK"}],
        "routing": {"rules": [{"ip": ["geoip:private"], "outboundTag": "BLOCK", "type": "field"}]},
    })


def route(exit_id=7, entry="VLESS_TCP", cascade="VLESS_TCP"):
    return {
        "entry_inbound_tag": entry,
        "exit_node_id": exit_id,
        "cascade_inbound_tag": cascade,
        "address": "10.0.0.2",
        "port": 8443,
        "uuid": "svc-uuid",
        "public_key": "PUB",
        "short_id": "abcd1234",
        "sni": "xapi.ozon.ru",
    }


def test_direct_role_returns_config_unchanged():
    cfg = base()
    assert cascade_config(cfg, role="direct") is cfg


def test_exit_injects_cascade_client_into_named_inbound():
    clients = [{"inbound_tag": "VLESS_TCP", "uuid": "svc-uuid"}]
    result = cascade_config(base(), role="exit", cascade_clients=clients)
    vless = next(i for i in result["inbounds"] if i["tag"] == "VLESS_TCP")
    ids = [c["id"] for c in vless["settings"]["clients"]]
    assert ids == ["user-1", "svc-uuid"]
    svc = vless["settings"]["clients"][-1]
    assert svc == {"id": "svc-uuid", "flow": "xtls-rprx-vision"}


def test_exit_leaves_other_inbounds_untouched():
    clients = [{"inbound_tag": "VLESS_TCP", "uuid": "svc-uuid"}]
    result = cascade_config(base(), role="exit", cascade_clients=clients)
    other = next(i for i in result["inbounds"] if i["tag"] == "OTHER")
    assert other["settings"]["clients"] == []


def test_exit_missing_inbound_is_noop():
    clients = [{"inbound_tag": "NOPE", "uuid": "svc-uuid"}]
    result = cascade_config(base(), role="exit", cascade_clients=clients)
    for i in result["inbounds"]:
        ids = [c["id"] for c in i["settings"]["clients"]]
        assert "svc-uuid" not in ids


def test_exit_is_idempotent_for_same_uuid():
    clients = [{"inbound_tag": "VLESS_TCP", "uuid": "svc-uuid"}]
    once = cascade_config(base(), role="exit", cascade_clients=clients)
    twice = cascade_config(once, role="exit", cascade_clients=clients)
    vless = next(i for i in twice["inbounds"] if i["tag"] == "VLESS_TCP")
    ids = [c["id"] for c in vless["settings"]["clients"]]
    assert ids.count("svc-uuid") == 1


def test_entry_adds_outbound_and_rule():
    result = cascade_config(base(), role="entry", entry_routes=[route(exit_id=7)])
    tag = cascade_outbound_tag(7, "VLESS_TCP")
    out_tags = [o["tag"] for o in result["outbounds"]]
    assert out_tags == ["DIRECT", "BLOCK", tag]
    out = result["outbounds"][-1]
    assert out["settings"]["vnext"][0]["address"] == "10.0.0.2"
    assert out["settings"]["vnext"][0]["port"] == 8443
    assert out["settings"]["vnext"][0]["users"][0]["id"] == "svc-uuid"
    assert out["settings"]["vnext"][0]["users"][0]["flow"] == "xtls-rprx-vision"
    assert out["streamSettings"]["realitySettings"]["publicKey"] == "PUB"
    assert out["streamSettings"]["realitySettings"]["serverName"] == "xapi.ozon.ru"
    assert out["streamSettings"]["realitySettings"]["shortId"] == "abcd1234"
    rule = result["routing"]["rules"][-1]
    assert rule == {"type": "field", "inboundTag": ["VLESS_TCP"], "outboundTag": tag}


def test_entry_outbound_tag_unique_per_exit_and_inbound():
    routes = [route(exit_id=7, cascade="VLESS_TCP"), route(exit_id=7, cascade="VLESS_WS")]
    result = cascade_config(base(), role="entry", entry_routes=routes)
    out_tags = [o["tag"] for o in result["outbounds"]]
    assert cascade_outbound_tag(7, "VLESS_TCP") in out_tags
    assert cascade_outbound_tag(7, "VLESS_WS") in out_tags


def test_entry_dedupes_outbound_for_same_exit_and_inbound():
    routes = [route(exit_id=7, entry="A", cascade="VLESS_TCP"),
              route(exit_id=7, entry="B", cascade="VLESS_TCP")]
    result = cascade_config(base(), role="entry", entry_routes=routes)
    tag = cascade_outbound_tag(7, "VLESS_TCP")
    out_tags = [o["tag"] for o in result["outbounds"]]
    assert out_tags.count(tag) == 1
    rules = [r for r in result["routing"]["rules"] if r.get("outboundTag") == tag]
    assert len(rules) == 2


def test_does_not_mutate_input():
    cfg = base()
    snapshot = copy.deepcopy(dict(cfg))
    cascade_config(cfg, role="entry", entry_routes=[route()])
    cascade_config(cfg, role="exit",
                   cascade_clients=[{"inbound_tag": "VLESS_TCP", "uuid": "svc-uuid"}])
    assert dict(cfg) == snapshot
