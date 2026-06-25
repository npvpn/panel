import types

from app.models.node import NodeStatus
from app.xray.host_addresses import resolve_host_addresses


def _node(address, status):
    return types.SimpleNamespace(address=address, status=status)


def _host(address, nodes):
    return types.SimpleNamespace(address=address, nodes=nodes)


def test_static_address_takes_priority_over_nodes():
    host = _host(
        "1.2.3.4, 5.6.7.8",
        [_node("9.9.9.9", NodeStatus.connected)],
    )
    assert resolve_host_addresses(host) == ["1.2.3.4", "5.6.7.8"]


def test_empty_address_collects_active_nodes_excluding_disabled():
    host = _host(
        "",
        [
            _node("10.0.0.1", NodeStatus.connected),
            _node("10.0.0.2", NodeStatus.disabled),
        ],
    )
    assert resolve_host_addresses(host) == ["10.0.0.1"]


def test_node_returns_from_disabled_reappears():
    node = _node("10.0.0.2", NodeStatus.disabled)
    host = _host("", [_node("10.0.0.1", NodeStatus.connected), node])
    assert resolve_host_addresses(host) == ["10.0.0.1"]
    node.status = NodeStatus.connecting
    assert resolve_host_addresses(host) == ["10.0.0.1", "10.0.0.2"]


def test_empty_address_no_nodes_returns_empty():
    assert resolve_host_addresses(_host("", [])) == []
