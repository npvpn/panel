"""Минимальный pytest-харнесс для панели.

app/__init__.py поднимает FastAPI и тяжёлые зависимости при импорте.
Чтобы тесты app.xray.inbound_filter (без БД/окружения) работали без полного
окружения, заглушаем app как пустой пакет до того, как pytest начнёт сбор.
"""

import pathlib
import sys
import types

_APP_DIR = pathlib.Path(__file__).parent.parent / "app"

# Регистрируем app как пустой пакет — тогда `from app.xray.inbound_filter import …`
# не запускает app/__init__.py, а берёт app.xray из реального файла.
if "app" not in sys.modules:
    app_stub = types.ModuleType("app")
    # Указываем реальный путь пакета, чтобы Python мог найти субмодули
    # (logging_config, logging_context, xray.*) без запуска app/__init__.py.
    app_stub.__path__ = [str(_APP_DIR)]
    app_stub.__package__ = "app"
    sys.modules["app"] = app_stub

if "app.xray" not in sys.modules:
    # Загружаем реальный app/xray/__init__.py напрямую через spec,
    # но он тоже тяжёлый — вместо этого регистрируем заглушку пакета,
    # и Python найдёт app/xray/inbound_filter.py через обычный механизм.
    xray_stub = types.ModuleType("app.xray")
    xray_stub.__path__ = [str(_APP_DIR / "xray")]
    xray_stub.__package__ = "app.xray"
    sys.modules["app.xray"] = xray_stub
