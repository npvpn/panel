"""Минимальный pytest-харнесс для панели.

app/__init__.py поднимает FastAPI и тяжёлые зависимости при импорте.
Чтобы тесты app.xray.inbound_filter (без БД/окружения) работали без полного
окружения, заглушаем app как пустой пакет до того, как pytest начнёт сбор.
"""
import pathlib
import sys
import types

_root = pathlib.Path(__file__).parent.parent

# Регистрируем app как пакет с path на app/, но без импорта app/__init__.py.
if "app" not in sys.modules:
    app_stub = types.ModuleType("app")
    app_stub.__path__ = [str(_root / "app")]
    sys.modules["app"] = app_stub

if "app.xray" not in sys.modules:
    xray_stub = types.ModuleType("app.xray")
    xray_stub.__path__ = [str(_root / "app" / "xray")]
    xray_stub.__package__ = "app.xray"
    sys.modules["app.xray"] = xray_stub

if "app.subscription" not in sys.modules:
    sub_stub = types.ModuleType("app.subscription")
    sub_stub.__path__ = [str(_root / "app" / "subscription")]
    sub_stub.__package__ = "app.subscription"
    sys.modules["app.subscription"] = sub_stub
