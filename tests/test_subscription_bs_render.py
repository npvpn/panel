"""Рендер БС-хостов подписки (NPVPN-1652): заглушка лимита и is_bs-routing.

Слой генерации (app/subscription/share.py::process_inbounds_and_tags) тянет тяжёлые
модули (app.templates → app.scheduler, app.utils.system → app.scheduler), которые в
песочнице tests/conftest.py недоступны. Заглушаем ровно их (шаблоны рендерим настоящим
jinja2 из app/templates), остальное — настоящие V2rayJsonConfig / share / bs_context.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
from collections import defaultdict

import jinja2
import pytest

_ROOT = pathlib.Path(__file__).parent.parent


def _stub_module(name: str, attrs: dict) -> types.ModuleType:
    """Дописать недостающие атрибуты в заглушку модуля (её мог завести другой тест)."""
    module = sys.modules.get(name) or types.ModuleType(name)
    for key, value in attrs.items():
        if getattr(module, key, None) is None:
            setattr(module, key, value)
    sys.modules[name] = module
    return module


# app.utils.system: тянет app.scheduler; в тестируемом пути нужны только эти функции.
_stub_module(
    "app.utils.system",
    {
        "get_public_ip": lambda: "127.0.0.1",
        "get_public_ipv6": lambda: "::1",
        "readable_size": lambda size: str(size),
    },
)


def _load_real_module(name: str, path: pathlib.Path) -> types.ModuleType:
    """Импортировать конкретный файл модуля напрямую, минуя app/templates/__init__.py
    (тот тянет app.utils.system → app.scheduler и не нужен: сами фильтры от него
    зависят только через readable_size, который уже застаблен выше)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# app.templates: настоящий пакет (через __init__.py) тянет app.utils.system → app.scheduler
# (весь FastAPI). Подменяем лёгким jinja-рендером тех же файлов app/templates/*, но с
# НАСТОЯЩИМИ кастомными фильтрами (yaml/except/only/...) из app/templates/filters.py —
# без них clash/singbox шаблоны не рендерятся (используют `| yaml`, `| except(...)`).
_templates_filters = _load_real_module("app.templates.filters", _ROOT / "app" / "templates" / "filters.py")
_env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(_ROOT / "app" / "templates")))
_env.filters.update(_templates_filters.CUSTOM_FILTERS)
_stub_module(
    "app.templates",
    {"render_template": lambda template, context=None: _env.get_template(template).render(context or {})},
)

from app.subscription.bs_context import ZERO_STUB, BsContext, StubEndpoint  # noqa: E402
from app.subscription.clash import ClashConfiguration, ClashMetaConfiguration  # noqa: E402
from app.subscription.outline import OutlineConfiguration  # noqa: E402
from app.subscription.singbox import SingBoxConfiguration  # noqa: E402
from app.subscription.v2ray import V2rayJsonConfig, V2rayShareLink  # noqa: E402

# share.py делает `from . import *`; в песочнице app/subscription/__init__.py не выполняется
# (conftest подменяет пакет), поэтому кладём классы конфигов в модуль пакета руками.
_subscription_pkg = sys.modules["app.subscription"]
for _name, _cls in {
    "ClashConfiguration": ClashConfiguration,
    "ClashMetaConfiguration": ClashMetaConfiguration,
    "OutlineConfiguration": OutlineConfiguration,
    "SingBoxConfiguration": SingBoxConfiguration,
    "V2rayJsonConfig": V2rayJsonConfig,
    "V2rayShareLink": V2rayShareLink,
}.items():
    setattr(_subscription_pkg, _name, _cls)

from app.subscription import share  # noqa: E402

BS_TAG = "VLESS_TCP"
BS_NODE_ID = 7
STUB_TEXT = "Лимит БС исчерпан"


class _Protocol:
    """Мини-замена ProxyTypes: process_inbounds_and_tags использует только .name."""

    name = "vless"


class _ProxySettings:
    def model_dump(self):
        return {"id": "00000000-0000-0000-0000-000000000000", "flow": ""}


class _FakeConf:
    """Не-V2rayJsonConfig конфиг: пишем в лог все add-вызовы."""

    def __init__(self):
        self.calls: list[dict] = []

    def add(self, remark, address, inbound, settings, **kwargs):
        self.calls.append({"remark": remark, "address": address, "inbound": inbound, "kwargs": kwargs})

    def render(self, reverse=False):
        return "rendered"


def _inbound() -> dict:
    return {
        "tag": BS_TAG,
        "network": "tcp",
        "protocol": "vless",
        "port": 443,
        "tls": "reality",
        "header_type": "",
        "fragment_setting": "",
        "noise_setting": "",
        "path": "",
        "sni": ["example.com"],
        "host": [],
        "fp": "chrome",
        "pbk": "pbk",
        "sid": "0123",
        "spx": "",
        "alpn": None,
        "ais": "",
    }


def _host(*addresses: str, node_ids: list[int] | None = None) -> dict:
    """Хост подписки: адрес — ДОМЕН (маскировка), нода привязана по node_ids."""
    return {
        "remark": "BS server",
        "address": list(addresses),
        "node_ids": list(node_ids or []),
        "port": 8443,
        "sni": [],
        "host": [],
        "path": None,
        "tls": None,
        "alpn": "",
        "fingerprint": "",
        "allowinsecure": False,
        "mux_enable": False,
        "fragment_setting": "",
        "noise_setting": "",
        "random_user_agent": False,
        "xhttp_extra": None,
        "use_sni_as_host": False,
        "bot_usernames": [],
    }


@pytest.fixture
def xray_stub(monkeypatch):
    """xray.config.inbounds_by_tag / xray.hosts — единственное, что share берёт из xray."""

    def _apply(hosts: list[dict]):
        inbound = _inbound()
        monkeypatch.setattr(
            share.xray,
            "config",
            types.SimpleNamespace(inbounds_by_tag={BS_TAG: inbound}),
            raising=False,
        )
        monkeypatch.setattr(share.xray, "hosts", {BS_TAG: hosts}, raising=False)

    return _apply


def _render(conf, bs: BsContext, stub: StubEndpoint = ZERO_STUB):
    # setup_format_variables тянет app.models.user → app.db; подставляем готовые переменные.
    format_variables = defaultdict(lambda: "<missing>", {"USERNAME": "u1", "BOT_USERNAME": None})
    protocol = _Protocol()
    return share.process_inbounds_and_tags(
        inbounds={protocol: [BS_TAG]},
        proxies={protocol: _ProxySettings()},
        format_variables=format_variables,
        conf=conf,
        bs=bs,
        stub=stub,
    )


def _blocked_ctx() -> BsContext:
    return BsContext(
        bs_node_ids=frozenset({BS_NODE_ID}),
        blocked_node_ids=frozenset({BS_NODE_ID}),
        stub_text=STUB_TEXT,
    )


def _bs_ctx() -> BsContext:
    return BsContext(bs_node_ids=frozenset({BS_NODE_ID}), blocked_node_ids=frozenset(), stub_text="")


def test_blocked_domain_host_renders_stub_with_text_address_and_port(xray_stub):
    """Ключевой кейс тикета: БС-хост задан ДОМЕНОМ, нода — по IP; хост заблокирован."""
    xray_stub([_host("bs.example.com", node_ids=[BS_NODE_ID])])
    conf = _FakeConf()
    stub = StubEndpoint(address="127.0.0.1", port=1)

    _render(conf, _blocked_ctx(), stub=stub)

    assert len(conf.calls) == 1
    call = conf.calls[0]
    assert call["remark"] == STUB_TEXT  # имя сервера-заглушки НЕ пустое
    assert call["address"] == stub.address
    assert call["inbound"]["port"] == stub.port
    assert call["kwargs"] == {}  # заглушка не получает is_bs


def test_non_bs_host_is_not_stubbed(xray_stub):
    xray_stub([_host("plain.example.com", node_ids=[42])])
    conf = _FakeConf()

    _render(conf, _blocked_ctx())

    assert conf.calls[0]["remark"] == "BS server"
    assert conf.calls[0]["address"] == "plain.example.com"


def _v2ray_json_conf() -> V2rayJsonConfig:
    template = {
        "remarks": "",
        "outbounds": [
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"},
        ],
        "routing": {"rules": [{"type": "field", "ip": ["geoip:ru"], "outboundTag": "direct"}]},
    }
    return V2rayJsonConfig(
        template_override=template,
        routing_default={"rules": [{"type": "field", "outboundTag": "direct", "domain": ["default"]}]},
        routing_bs={"rules": [{"type": "field", "outboundTag": "direct", "domain": ["bs"]}]},
    )


def _routing_domains(conf: V2rayJsonConfig) -> list[str]:
    return [rule.get("domain", [""])[0] for rule in conf.config[-1]["routing"]["rules"]]


def test_v2ray_json_single_address_bs_host_gets_bs_routing(xray_stub):
    """is_bs=True доходит до V2rayJsonConfig.add → выбирается routing_bs."""
    xray_stub([_host("bs.example.com", node_ids=[BS_NODE_ID])])
    conf = _v2ray_json_conf()

    _render(conf, _bs_ctx())

    assert len(conf.config) == 1
    assert _routing_domains(conf) == ["bs"]


def test_v2ray_json_balanced_bs_host_gets_bs_routing(xray_stub):
    """Мульти-адресный (балансируемый) БС-хост → add_balanced(is_bs=True)."""
    xray_stub([_host("bs1.example.com", "bs2.example.com", node_ids=[BS_NODE_ID])])
    conf = _v2ray_json_conf()

    _render(conf, _bs_ctx())

    cfg = conf.config[-1]
    proxy_tags = [o["tag"] for o in cfg["outbounds"] if o["tag"].startswith("proxy")]
    assert proxy_tags == ["proxy", "proxy-1"]  # балансировка сохранена
    assert "bs" in _routing_domains(conf)  # и БС-routing тоже


def test_v2ray_json_non_bs_host_gets_default_routing(xray_stub):
    xray_stub([_host("plain.example.com", node_ids=[42])])
    conf = _v2ray_json_conf()

    _render(conf, _bs_ctx())

    assert _routing_domains(conf) == ["default"]


def test_is_bs_never_leaks_into_other_formats(xray_stub):
    """Другие форматы про is_bs не знают — их conf.add вызывается без него."""
    xray_stub([_host("bs.example.com", node_ids=[BS_NODE_ID])])
    conf = _FakeConf()

    _render(conf, _bs_ctx())

    assert conf.calls[0]["kwargs"] == {}
    assert conf.calls[0]["remark"] == "BS server"


# _FakeConf.add(**kwargs) молча проглотит лишний is_bs, если isinstance-гвард
# (`isinstance(conf, V2rayJsonConfig)` в share.py) снять — assert kwargs == {} выше
# страхует только сам факт "kwargs пустой", но не докажет, что ДРУГИЕ форматы вообще
# не умеют принять is_bs. Настоящие ClashConfiguration/ClashMetaConfiguration/
# SingBoxConfiguration/OutlineConfiguration.add() параметра is_bs не имеют — при снятии
# гварда process_inbounds_and_tags упал бы TypeError'ом (500 на подписке). Прогоняем
# process_inbounds_and_tags с настоящими классами, чтобы рендер БС-хоста в этих форматах
# доказуемо не падал (а при регрессии гварда — падал бы).
@pytest.mark.parametrize(
    "conf_factory",
    [ClashConfiguration, ClashMetaConfiguration, SingBoxConfiguration, OutlineConfiguration],
    ids=["clash", "clash_meta", "singbox", "outline"],
)
def test_is_bs_host_renders_without_error_in_real_non_v2ray_formats(xray_stub, conf_factory):
    xray_stub([_host("bs.example.com", node_ids=[BS_NODE_ID])])
    conf = conf_factory()

    rendered = _render(conf, _bs_ctx())

    assert rendered  # рендер прошёл до конца, а не упал TypeError'ом на лишнем kwarg


# --- build_bs_context: stub_text считается от node-id-пути, а не от адресов ---
# app.db тянет SQLAlchemy-модели и коннект к MySQL — в песочнице недоступен,
# подменяем модулем с фейковым crud (Session/User нужны только как аннотации).
_fake_crud = types.SimpleNamespace(
    get_blocked_bs_node_ids=lambda db, user_id: set(db["blocked"]),
    get_bs_node_ids=lambda db: set(db["bs"]),
)
_stub_module("app.db", {"Session": dict, "crud": _fake_crud})
_stub_module("app.db.models", {"User": types.SimpleNamespace})

from app.subscription.bs_context_builder import build_bs_context  # noqa: E402

BS_SETTINGS = {"sub_bs_limit_server_text": ["Лимит БС исчерпан"]}


def test_build_bs_context_sets_stub_text_for_blocked_domain_host():
    """Баг: раньше stub_text брался от адресного множества → у доменного БС-хоста
    заглушка получала ПУСТОЕ имя. Теперь текст зависит от блоков по node_ids."""
    bs = build_bs_context(
        {"bs": {BS_NODE_ID}, "blocked": {BS_NODE_ID}},
        types.SimpleNamespace(id=1),
        is_revoked=False,
        is_expired=False,
        bot_settings=BS_SETTINGS,
    )
    assert bs.bs_node_ids == frozenset({BS_NODE_ID})
    assert bs.blocked_node_ids == frozenset({BS_NODE_ID})
    assert bs.has_blocks is True
    assert bs.stub_text  # имя сервера-заглушки не пустое
    assert bs.is_bs(_host("bs.example.com", node_ids=[BS_NODE_ID])) is True
    assert bs.is_blocked(_host("bs.example.com", node_ids=[BS_NODE_ID])) is True


def test_build_bs_context_without_blocks_has_no_stub_text():
    bs = build_bs_context(
        {"bs": {BS_NODE_ID}, "blocked": set()},
        types.SimpleNamespace(id=1),
        is_revoked=False,
        is_expired=False,
        bot_settings=BS_SETTINGS,
    )
    assert bs.has_blocks is False
    assert bs.stub_text == ""


def test_build_bs_context_is_empty_for_revoked_or_expired():
    db = {"bs": {BS_NODE_ID}, "blocked": {BS_NODE_ID}}
    user = types.SimpleNamespace(id=1)
    revoked = build_bs_context(db, user, is_revoked=True, is_expired=False, bot_settings=BS_SETTINGS)
    expired = build_bs_context(db, user, is_revoked=False, is_expired=True, bot_settings=BS_SETTINGS)
    assert revoked == BsContext.empty()
    assert expired == BsContext.empty()
