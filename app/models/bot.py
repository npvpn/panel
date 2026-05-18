from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from config import (
    BOT_URL,
    SUB_CLIENT_NOTE,
    SUB_DEVICE_LIMIT_ANNOUNCE_TEXT,
    SUB_DEVICE_LIMIT_SERVER_TEXT,
    SUB_EXPIRED_ANNOUNCE_TEXT,
    SUB_EXPIRED_SERVER_TEXT,
    SUB_PROFILE_TITLE,
    SUB_PROFILE_URL,
    SUB_REVOKED_ANNOUNCE_TEXT,
    SUB_REVOKED_SERVER_TEXT,
    SUB_ROUTING_HAPP,
    SUB_ROUTING_V2RAYTUN,
    SUB_SUPPORT_URL,
    SUB_UNSUPPORTED_CLIENT_ANNOUNCE_TEXT,
    SUB_UNSUPPORTED_CLIENT_SERVER_TEXT,
    SUB_UPDATE_INTERVAL,
)


def _normalize_server_text(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


DEFAULT_BOT_SETTINGS: Dict[str, Any] = {
    "sub_update_interval": str(SUB_UPDATE_INTERVAL),
    "sub_support_url": SUB_SUPPORT_URL,
    "sub_profile_title": SUB_PROFILE_TITLE,
    "sub_routing_happ": SUB_ROUTING_HAPP,
    "sub_routing_v2raytun": SUB_ROUTING_V2RAYTUN,
    "sub_client_note": SUB_CLIENT_NOTE,
    "sub_profile_url": SUB_PROFILE_URL,
    "bot_url": BOT_URL,
    "sub_revoked_announce_text": SUB_REVOKED_ANNOUNCE_TEXT,
    "sub_expired_announce_text": SUB_EXPIRED_ANNOUNCE_TEXT,
    "sub_device_limit_announce_text": SUB_DEVICE_LIMIT_ANNOUNCE_TEXT,
    "sub_unsupported_client_announce_text": SUB_UNSUPPORTED_CLIENT_ANNOUNCE_TEXT,
    "sub_revoked_server_text": _normalize_server_text(SUB_REVOKED_SERVER_TEXT),
    "sub_expired_server_text": _normalize_server_text(SUB_EXPIRED_SERVER_TEXT),
    "sub_device_limit_server_text": _normalize_server_text(SUB_DEVICE_LIMIT_SERVER_TEXT),
    "sub_unsupported_client_server_text": _normalize_server_text(SUB_UNSUPPORTED_CLIENT_SERVER_TEXT),
}


class BotBase(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    title: Optional[str] = Field(None, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str):
        return value.strip().lstrip("@")


class BotCreate(BotBase):
    pass


class BotUpdate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    title: Optional[str] = Field(None, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str):
        return value.strip().lstrip("@")


class BotResponse(BotBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class BotSettingsPayload(BaseModel):
    sub_update_interval: str = ""
    sub_support_url: str = ""
    sub_profile_title: str = ""
    sub_routing_happ: str = ""
    sub_routing_v2raytun: str = ""
    sub_client_note: str = ""
    sub_profile_url: str = ""
    bot_url: str = ""
    sub_revoked_announce_text: str = ""
    sub_expired_announce_text: str = ""
    sub_device_limit_announce_text: str = ""
    sub_unsupported_client_announce_text: str = ""
    sub_revoked_server_text: List[str] = []
    sub_expired_server_text: List[str] = []
    sub_device_limit_server_text: List[str] = []
    sub_unsupported_client_server_text: List[str] = []

    @field_validator(
        "sub_revoked_server_text",
        "sub_expired_server_text",
        "sub_device_limit_server_text",
        "sub_unsupported_client_server_text",
        mode="before",
    )
    @classmethod
    def validate_server_text(cls, value: Any):
        return _normalize_server_text(value)


def apply_bot_settings_fallback(raw_settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = dict(DEFAULT_BOT_SETTINGS)
    if raw_settings:
        for key, value in raw_settings.items():
            if value is not None:
                base[key] = value

    for key in (
        "sub_revoked_server_text",
        "sub_expired_server_text",
        "sub_device_limit_server_text",
        "sub_unsupported_client_server_text",
    ):
        base[key] = _normalize_server_text(base.get(key))

    return base
