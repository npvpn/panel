from __future__ import annotations

from typing import Any

from config import XRAY_SUBSCRIPTION_PATH, XRAY_SUBSCRIPTION_URL_PREFIX


def normalize_subscription_domain(value: str | None) -> str:
    """Strip scheme/slashes; store/display as example.net."""
    return str(value or "").strip().replace("https://", "").replace("http://", "").strip("/")


def resolve_subscription_url_prefix(bot_settings: dict[str, Any] | None = None) -> str:
    """Bot domain → https://{domain}; else XRAY_SUBSCRIPTION_URL_PREFIX; else empty."""
    domain = normalize_subscription_domain((bot_settings or {}).get("sub_subscription_domain"))
    if domain:
        return f"https://{domain}"
    return (XRAY_SUBSCRIPTION_URL_PREFIX or "").strip("/")


def build_subscription_url(
    token: str | None,
    prefix: str | None = None,
    *,
    bot_settings: dict[str, Any] | None = None,
) -> str:
    """Assemble /{path}/{token}, optionally with an absolute prefix."""
    if not token:
        return ""
    url_prefix = (prefix if prefix is not None else resolve_subscription_url_prefix(bot_settings)).strip("/")
    path = f"/{XRAY_SUBSCRIPTION_PATH}/{token}"
    return f"{url_prefix}{path}" if url_prefix else path
