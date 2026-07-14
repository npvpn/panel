from app.subscription.bs_context import ZERO_STUB, BsContext, StubEndpoint


def host(*node_ids):
    return {"address": ["example.com"], "node_ids": list(node_ids)}


def ctx(bs=(), blocked=(), stub_text="лимит"):
    return BsContext(bs_node_ids=frozenset(bs), blocked_node_ids=frozenset(blocked), stub_text=stub_text)


def test_host_with_domain_bound_to_bs_node_is_bs():
    # Ключевой кейс NPVPN-1652: адрес хоста — домен, нода подключена по IP.
    assert ctx(bs=[7]).is_bs(host(7)) is True


def test_host_without_nodes_is_never_bs():
    assert ctx(bs=[7]).is_bs(host()) is False
    assert ctx(bs=[7]).is_bs({"address": ["192.0.2.10"]}) is False


def test_multi_node_host_is_bs_when_any_node_is_bs():
    assert ctx(bs=[7]).is_bs(host(3, 7)) is True
    assert ctx(bs=[7]).is_bs(host(3, 4)) is False


def test_is_blocked_by_node_link():
    assert ctx(bs=[7], blocked=[7]).is_blocked(host(7)) is True
    assert ctx(bs=[7], blocked=[7]).is_blocked(host(3)) is False
    assert ctx(bs=[7], blocked=[7]).is_blocked(host(3, 7)) is True


def test_empty_context_matches_nothing():
    empty = BsContext.empty()
    assert empty.is_bs(host(7)) is False
    assert empty.is_blocked(host(7)) is False
    assert empty.has_blocks is False
    assert empty.stub_text == ""


def test_has_blocks_reflects_blocked_nodes():
    assert ctx(bs=[7], blocked=[7]).has_blocks is True
    assert ctx(bs=[7]).has_blocks is False


def test_zero_stub_endpoint():
    assert ZERO_STUB == StubEndpoint(address="0.0.0.0", port=0)
