"""Минимальный pytest-харнесс для панели.

app/__init__.py поднимает FastAPI и тяжёлые зависимости при импорте.
Чтобы тесты app.xray.inbound_filter (без БД/окружения) работали без полного
окружения, заглушаем app как пустой пакет до того, как pytest начнёт сбор.
"""
import sys
import types

# Регистрируем app как пустой пакет — тогда `from app.xray.inbound_filter import …`
# не запускает app/__init__.py, а берёт app.xray из реального файла.
if "app" not in sys.modules:
    app_stub = types.ModuleType("app")
    app_stub.__path__ = []  # тип пакета, а не просто модуль
    sys.modules["app"] = app_stub

if "app.xray" not in sys.modules:
    import pathlib

    # Загружаем реальный app/xray/__init__.py напрямую через spec,
    # но он тоже тяжёлый — вместо этого регистрируем заглушку пакета,
    # и Python найдёт app/xray/inbound_filter.py через обычный механизм.
    xray_stub = types.ModuleType("app.xray")
    xray_stub.__path__ = [str(pathlib.Path(__file__).parent.parent / "app" / "xray")]
    xray_stub.__package__ = "app.xray"
    sys.modules["app.xray"] = xray_stub

if "app.subscription" not in sys.modules:
    import pathlib

    # Заглушка пакета app.subscription с реальным путём — Python найдёт
    # app/subscription/custom_headers.py, не выполняя app/subscription/__init__.py.
    subscription_stub = types.ModuleType("app.subscription")
    subscription_stub.__path__ = [
        str(pathlib.Path(__file__).parent.parent / "app" / "subscription")
    ]
    subscription_stub.__package__ = "app.subscription"
    sys.modules["app.subscription"] = subscription_stub
