from __future__ import annotations

from typing import Any

from app.models.settings import PLATFORMS, merge_client_apps_defaults

# На Apple-платформах ссылка зависит от региона Apple ID, на остальных она одна.
_APPLE_LINK_KEYS: dict[str, tuple[str, str]] = {
    "ios": ("ios_ru", "ios_global"),
    "macos": ("macos_ru", "macos_global"),
}


def _app_view(app: dict[str, Any], platform: str) -> dict[str, Any] | None:
    """Вид приложения на платформе. None — если под эту платформу ссылок нет."""
    links = app.get("links") or {}

    if platform in _APPLE_LINK_KEYS:
        ru_key, global_key = _APPLE_LINK_KEYS[platform]
        install = [
            {"region": region, "url": links.get(key) or ""}
            for region, key in (("ru", ru_key), ("global", global_key))
            if links.get(key)
        ]
    else:
        url = links.get(platform) or ""
        install = [{"region": "default", "url": url}] if url else []

    if not install:
        return None

    return {
        "id": app["id"],
        "name": app["name"],
        "scheme": app["scheme"],
        "install": install,
    }


def build_client_apps_view(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Настройки приложений в виде, готовом для шаблона страницы подписки."""
    settings = merge_client_apps_defaults(raw)
    enabled_apps = [app for app in settings["apps"] if app.get("enabled")]
    primary_by_platform = settings.get("primary_by_platform") or {}

    platforms: dict[str, Any] = {}
    for platform in PLATFORMS:
        primary_id = primary_by_platform.get(platform) or ""

        primary: dict[str, Any] | None = None
        alternatives: list[dict[str, Any]] = []
        for app in enabled_apps:
            view = _app_view(app, platform)
            if view is None:
                continue
            if app["id"] == primary_id:
                primary = view
            else:
                alternatives.append(view)

        # Главное приложение без ссылок под платформу (например, Happ выпилили из стора)
        # не должно оставлять страницу без кнопки установки.
        if primary is None and alternatives:
            primary, alternatives = alternatives[0], alternatives[1:]

        platforms[platform] = {"primary": primary, "alternatives": alternatives}

    return {"platforms": platforms}
