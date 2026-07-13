from __future__ import annotations

from typing import Any

from app.db import Session, crud
from app.models.settings import CLIENT_APPS_KEY, ClientAppsPayload, merge_client_apps_defaults


def get_client_apps(db: Session) -> dict[str, Any]:
    """Текущие настройки приложений, дополненные дефолтами."""
    return merge_client_apps_defaults(crud.get_global_setting(db, CLIENT_APPS_KEY))


def save_client_apps(db: Session, payload: ClientAppsPayload) -> dict[str, Any]:
    """Сохранить настройки приложений (payload уже провалидирован pydantic)."""
    stored = crud.upsert_global_setting(db, CLIENT_APPS_KEY, payload.model_dump())
    return merge_client_apps_defaults(stored)
