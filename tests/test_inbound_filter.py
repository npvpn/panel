from app.xray.inbound_filter import filtered_inbounds

# Набор инбаундов как в config["inbounds"]: инфраструктурные (API) + управляемые прокси-инбаунды.
INBOUNDS = [
    {"tag": "API_INBOUND", "protocol": "dokodemo-door"},
    {"tag": "VLESS_TCP", "protocol": "vless"},
    {"tag": "VMESS_WS", "protocol": "vmess"},
    {"tag": "TROJAN_TCP", "protocol": "trojan"},
]
MANAGED = {"VLESS_TCP", "VMESS_WS", "TROJAN_TCP"}  # config.inbounds_by_tag.keys()


def test_keeps_only_allowed_managed_inbounds():
    result = filtered_inbounds(INBOUNDS, managed_tags=MANAGED, allowed_tags={"VLESS_TCP"})
    tags = [i["tag"] for i in result]
    assert tags == ["API_INBOUND", "VLESS_TCP"]


def test_infra_inbounds_always_kept():
    # API_INBOUND не входит в managed, значит остаётся всегда, даже если allowed пуст.
    result = filtered_inbounds(INBOUNDS, managed_tags=MANAGED, allowed_tags=set())
    assert [i["tag"] for i in result] == ["API_INBOUND"]


def test_multiple_allowed():
    result = filtered_inbounds(INBOUNDS, managed_tags=MANAGED, allowed_tags={"VLESS_TCP", "TROJAN_TCP"})
    assert [i["tag"] for i in result] == ["API_INBOUND", "VLESS_TCP", "TROJAN_TCP"]


def test_does_not_mutate_input():
    snapshot = [dict(i) for i in INBOUNDS]
    filtered_inbounds(INBOUNDS, managed_tags=MANAGED, allowed_tags={"VLESS_TCP"})
    assert INBOUNDS == snapshot


def test_unknown_allowed_tag_ignored():
    result = filtered_inbounds(INBOUNDS, managed_tags=MANAGED, allowed_tags={"NOPE"})
    assert [i["tag"] for i in result] == ["API_INBOUND"]


from app.xray.inbound_filter import apply_inbound_filter


class FakeConfig(dict):
    """Мимикрия XRayConfig: dict + .copy() (deep) + .inbounds_by_tag."""

    def __init__(self, *args, inbounds_by_tag=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._inbounds_by_tag = inbounds_by_tag or {}

    @property
    def inbounds_by_tag(self):
        return self._inbounds_by_tag

    def copy(self):
        clone = FakeConfig(inbounds_by_tag=self._inbounds_by_tag)
        clone["inbounds"] = [dict(i) for i in self["inbounds"]]
        return clone


def _base_config():
    return FakeConfig(
        {"inbounds": [dict(i) for i in INBOUNDS]},
        inbounds_by_tag={tag: {} for tag in MANAGED},
    )


def test_apply_empty_returns_same_object():
    cfg = _base_config()
    assert apply_inbound_filter(cfg, []) is cfg


def test_apply_subset_keeps_infra_and_allowed():
    cfg = _base_config()
    result = apply_inbound_filter(cfg, ["VLESS_TCP"])
    assert result is not cfg
    assert [i["tag"] for i in result["inbounds"]] == ["API_INBOUND", "VLESS_TCP"]
    # исходный конфиг не мутирован
    assert [i["tag"] for i in cfg["inbounds"]] == [i["tag"] for i in INBOUNDS]


def test_apply_unknown_tag_ignored():
    cfg = _base_config()
    result = apply_inbound_filter(cfg, ["NOPE"])
    assert [i["tag"] for i in result["inbounds"]] == ["API_INBOUND"]
