"""NPVPN-1533: xhttp_extra на хосте — валидация JSON-объекта."""

from __future__ import annotations

import sys
import types

import pytest

# app.models.proxy тянет app.utils.system (random_password), а тот на импорте
# делает `from app import scheduler` — при заглушенном пакете app (см. conftest)
# это падает ImportError. Заглушаем app.utils.system минимальной реализацией:
# в тестируемом пути (валидация xhttp_extra) random_password не вызывается.
if "app.utils.system" not in sys.modules:
    _system_stub = types.ModuleType("app.utils.system")
    _system_stub.random_password = lambda *a, **kw: "stub"
    sys.modules["app.utils.system"] = _system_stub

from app.models.proxy import ProxyHost


def _host(**kw):
    return ProxyHost(remark="r", address="a", **kw)


def test_xhttp_extra_accepts_dict():
    h = _host(xhttp_extra={"xPaddingMethod": "tokenish"})
    assert h.xhttp_extra == {"xPaddingMethod": "tokenish"}


def test_xhttp_extra_accepts_none():
    assert _host().xhttp_extra is None


def test_xhttp_extra_rejects_list():
    with pytest.raises(ValueError):
        _host(xhttp_extra=["not", "an", "object"])


def test_xhttp_extra_rejects_scalar():
    with pytest.raises(ValueError):
        _host(xhttp_extra="oops")
