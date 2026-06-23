import ast
import copy
import pathlib

from app.xray.cascade_config import (
    cascade_balancer_tag,
    cascade_config,
    cascade_outbound_tag,
)


class FakeConfig(dict):
    """Имитирует XRayConfig: .copy() делает deepcopy (как в app/xray/config.py)."""

    def copy(self):
        return FakeConfig(copy.deepcopy(dict(self)))


def base():
    return FakeConfig(
        {
            "inbounds": [
                {
                    "tag": "VLESS_TCP",
                    "protocol": "vless",
                    "settings": {"clients": [{"id": "user-1"}], "decryption": "none"},
                },
                {"tag": "OTHER", "protocol": "vless", "settings": {"clients": []}},
            ],
            "outbounds": [{"protocol": "freedom", "tag": "DIRECT"}, {"protocol": "blackhole", "tag": "BLOCK"}],
            "routing": {"rules": [{"ip": ["geoip:private"], "outboundTag": "BLOCK", "type": "field"}]},
        }
    )


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


def test_entry_uses_fingerprint_from_route():
    r = route(exit_id=7)
    r["fingerprint"] = "qq"
    result = cascade_config(base(), role="entry", entry_routes=[r])
    out = result["outbounds"][-1]
    assert out["streamSettings"]["realitySettings"]["fingerprint"] == "qq"


def test_entry_fingerprint_falls_back_to_default_when_absent():
    result = cascade_config(base(), role="entry", entry_routes=[route()])
    out = result["outbounds"][-1]
    assert out["streamSettings"]["realitySettings"]["fingerprint"] == "chrome"


def test_entry_fingerprint_falls_back_to_default_when_empty():
    r = route(exit_id=7)
    r["fingerprint"] = ""
    result = cascade_config(base(), role="entry", entry_routes=[r])
    out = result["outbounds"][-1]
    assert out["streamSettings"]["realitySettings"]["fingerprint"] == "chrome"


def test_entry_outbound_tag_unique_per_exit_and_inbound():
    routes = [route(exit_id=7, cascade="VLESS_TCP"), route(exit_id=7, cascade="VLESS_WS")]
    result = cascade_config(base(), role="entry", entry_routes=routes)
    out_tags = [o["tag"] for o in result["outbounds"]]
    assert cascade_outbound_tag(7, "VLESS_TCP") in out_tags
    assert cascade_outbound_tag(7, "VLESS_WS") in out_tags


def test_entry_dedupes_outbound_for_same_exit_and_inbound():
    routes = [route(exit_id=7, entry="A", cascade="VLESS_TCP"), route(exit_id=7, entry="B", cascade="VLESS_TCP")]
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
    cascade_config(cfg, role="exit", cascade_clients=[{"inbound_tag": "VLESS_TCP", "uuid": "svc-uuid"}])
    assert dict(cfg) == snapshot


def test_entry_single_route_per_inbound_keeps_outbound_rule():
    # одна route на entry_inbound_tag → старое поведение, без балансировщика
    result = cascade_config(base(), role="entry", entry_routes=[route(exit_id=7)], strategy="leastPing")
    assert "balancers" not in result["routing"]
    rule = result["routing"]["rules"][-1]
    assert rule == {"type": "field", "inboundTag": ["VLESS_TCP"], "outboundTag": cascade_outbound_tag(7, "VLESS_TCP")}
    # observatory не добавляется, если нет ни одного балансировщика
    assert "observatory" not in result


def test_entry_multiple_exits_same_inbound_build_balancer():
    routes = [
        route(exit_id=7, entry="VLESS_TCP", cascade="VLESS_TCP"),
        route(exit_id=9, entry="VLESS_TCP", cascade="VLESS_TCP"),
    ]
    result = cascade_config(base(), role="entry", entry_routes=routes, strategy="random")

    # оба outbound'а присутствуют
    out_tags = [o["tag"] for o in result["outbounds"]]
    assert cascade_outbound_tag(7, "VLESS_TCP") in out_tags
    assert cascade_outbound_tag(9, "VLESS_TCP") in out_tags

    # один балансировщик с явным selector'ом из тегов группы
    bal_tag = cascade_balancer_tag("VLESS_TCP")
    balancers = result["routing"]["balancers"]
    assert len(balancers) == 1
    bal = balancers[0]
    assert bal["tag"] == bal_tag
    assert bal["selector"] == [cascade_outbound_tag(7, "VLESS_TCP"), cascade_outbound_tag(9, "VLESS_TCP")]
    assert bal["strategy"] == {"type": "random"}

    # одно routing-правило входного инбаунда → balancerTag (а не два outboundTag)
    inbound_rules = [r for r in result["routing"]["rules"] if r.get("inboundTag") == ["VLESS_TCP"]]
    assert inbound_rules == [{"type": "field", "inboundTag": ["VLESS_TCP"], "balancerTag": bal_tag}]


def test_entry_observatory_only_for_least_ping():
    routes = [route(exit_id=7), route(exit_id=9)]
    result = cascade_config(base(), role="entry", entry_routes=routes, strategy="leastPing")
    assert result["observatory"] == {
        "subjectSelector": ["CASCADE_OUT_"],
        "probeUrl": "https://www.google.com/generate_204",
        "probeInterval": "10s",
    }
    assert "burstObservatory" not in result
    assert result["routing"]["balancers"][0]["strategy"] == {"type": "leastPing"}


def test_entry_burst_observatory_only_for_least_load():
    routes = [route(exit_id=7), route(exit_id=9)]
    result = cascade_config(base(), role="entry", entry_routes=routes, strategy="leastLoad")
    assert result["burstObservatory"] == {
        "subjectSelector": ["CASCADE_OUT_"],
        "pingConfig": {
            "destination": "https://www.google.com/generate_204",
            "interval": "10s",
            "connectivity": "",
            "timeout": "3s",
            "sampling": 3,
        },
    }
    assert "observatory" not in result
    assert result["routing"]["balancers"][0]["strategy"] == {"type": "leastLoad"}


def test_entry_random_round_robin_have_no_observatory():
    routes = [route(exit_id=7), route(exit_id=9)]
    for strat in ("random", "roundRobin"):
        result = cascade_config(base(), role="entry", entry_routes=routes, strategy=strat)
        assert "observatory" not in result
        assert "burstObservatory" not in result


def test_entry_unknown_strategy_falls_back_to_random():
    routes = [route(exit_id=7), route(exit_id=9)]
    result = cascade_config(base(), role="entry", entry_routes=routes, strategy="bogus")
    assert result["routing"]["balancers"][0]["strategy"] == {"type": "random"}
    assert "observatory" not in result
    assert "burstObservatory" not in result


def test_entry_two_groups_get_separate_balancers():
    routes = [
        route(exit_id=7, entry="VLESS_TCP", cascade="VLESS_TCP"),
        route(exit_id=9, entry="VLESS_TCP", cascade="VLESS_TCP"),
        route(exit_id=7, entry="OTHER", cascade="VLESS_TCP"),
        route(exit_id=9, entry="OTHER", cascade="VLESS_TCP"),
    ]
    result = cascade_config(base(), role="entry", entry_routes=routes, strategy="random")
    bal_tags = {b["tag"] for b in result["routing"]["balancers"]}
    assert bal_tags == {cascade_balancer_tag("VLESS_TCP"), cascade_balancer_tag("OTHER")}


def test_entry_appends_cascade_rules_after_base_rules():
    """Documents the rule-ordering invariant: cascade rules are appended after base rules.

    xray is first-match-wins; the base config must not carry an earlier rule matching
    a cascade entry_inbound_tag or the cascade balancer/outbound rule would be dead.
    This test asserts the base BLOCK rule stays first and the balancer rule follows it.
    """
    routes = [
        route(exit_id=7, entry="VLESS_TCP", cascade="VLESS_TCP"),
        route(exit_id=9, entry="VLESS_TCP", cascade="VLESS_TCP"),
    ]
    result = cascade_config(base(), role="entry", entry_routes=routes, strategy="random")
    rules = result["routing"]["rules"]
    # The pre-existing base rule is still present and still first.
    assert rules[0] == {"ip": ["geoip:private"], "outboundTag": "BLOCK", "type": "field"}
    # The appended balancer rule appears after it.
    bal_tag = cascade_balancer_tag("VLESS_TCP")
    balancer_rules = [r for r in rules if r.get("balancerTag") == bal_tag]
    assert len(balancer_rules) == 1
    assert rules.index(balancer_rules[0]) > 0


def _strategy_values_from_source():
    """NodeBalancerStrategy member values straight from source (no import — the
    test venv can't import app.models; see project_venv_app_import memory)."""
    src = pathlib.Path("app/models/node.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "NodeBalancerStrategy":
            return {
                stmt.value.value
                for stmt in node.body
                if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant)
            }
    raise AssertionError("NodeBalancerStrategy not found in app/models/node.py")


def test_migration_enum_matches_strategy_values():
    """Regression for the 'Data truncated' bug: the SQL ENUM declared in the
    migration must list NodeBalancerStrategy *values* (e.g. "leastLoad"), because
    the ORM column uses values_callable to persist values rather than member names
    (e.g. "least_load"). If these drift, MySQL truncates on any non-trivial member.
    """
    migration = pathlib.Path("app/db/migrations/versions/e1f2a3b4c5d6_node_cascade_balancer_strategy.py").read_text()
    tree = ast.parse(migration)
    enum_args = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "Enum":
            enum_args = [a.value for a in node.args if isinstance(a, ast.Constant)]
            break
    assert enum_args is not None, "sa.Enum(...) not found in migration"
    assert set(enum_args) == _strategy_values_from_source()
