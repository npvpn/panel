from __future__ import annotations

from app.db import Session, crud
from app.models.settings import CLIENT_APPS_KEY
from app.models.user import UserResponse
from app.subscription.bot_settings import resolve_bot_settings
from app.subscription.client_apps import build_client_apps_view
from app.subscription.user_info import devices_json
from config import XRAY_SUBSCRIPTION_PATH


def build_subscription_page_context(db: Session, dbuser, token: str) -> dict:
    """Контекст jinja-шаблона страницы подписки (HTML-ветка)."""
    bot_settings = resolve_bot_settings(dbuser)
    devices = crud.get_user_active_devices(db, dbuser)
    return {
        "user": UserResponse.model_validate(dbuser),
        "devices": devices,
        "devices_json": devices_json(devices),
        "token": token,
        "sub_path": XRAY_SUBSCRIPTION_PATH,
        "web_url": (bot_settings.get("web_url") or "").strip(),
        "bot_url": bot_settings["bot_url"],
        "show_ads": bool(bot_settings.get("show_ads", True)),
        "client_apps": build_client_apps_view(crud.get_global_setting(db, CLIENT_APPS_KEY)),
    }
