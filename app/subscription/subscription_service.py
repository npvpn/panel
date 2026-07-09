import re
from collections.abc import Callable
from typing import Literal, NamedTuple, TypedDict

from fastapi import Request

from app.models.user import UserResponse
from app.subscription.custom_headers import parse_custom_headers
from app.subscription.share import encode_title

# Сервисный модуль для /sub-эндпоинтов:
# - выбор плана рендера подписки (формат/тип ответа),
# - сбор общих response headers,
# - вычисление announce-текста.
SubscriptionConfigFormat = Literal["v2ray", "clash-meta", "clash", "sing-box", "outline", "v2ray-json", "incy"]


class SubscriptionClientConfigEntry(TypedDict):
    config_format: SubscriptionConfigFormat
    media_type: str
    as_base64: bool
    reverse: bool


class SubscriptionRenderPlan(NamedTuple):
    """Нормализованный план ответа для подписки."""

    config_format: SubscriptionConfigFormat
    as_base64: bool
    reverse: bool
    media_type: str


def _version_gte(version_str: str, min_version: str) -> bool:
    """Лёгкое сравнение версий без distutils (mypy-friendly)."""

    def parse(v: str) -> tuple[int, ...]:
        return tuple(int(part) for part in v.split("."))

    return parse(version_str) >= parse(min_version)


def resolve_announce_text(
    user: UserResponse,
    *,
    is_revoked: bool,
    is_expired: bool,
    device_limited: bool,
    unsupported_blocks: bool,
    blocked_bs_addresses: set,
    bot_settings: dict,
    get_user_note: Callable[[UserResponse, str], str],
) -> str:
    # Приоритет announce совпадает с историческим поведением роутера.
    announce_text = get_user_note(user, str(bot_settings["sub_client_note"])) or ""
    if is_revoked and str(bot_settings["sub_revoked_announce_text"]).strip():
        return get_user_note(user, bot_settings["sub_revoked_announce_text"])
    if is_expired and str(bot_settings["sub_expired_announce_text"]).strip():
        return get_user_note(user, bot_settings["sub_expired_announce_text"])
    if device_limited and str(bot_settings["sub_device_limit_announce_text"]).strip():
        return get_user_note(user, bot_settings["sub_device_limit_announce_text"])
    if unsupported_blocks and str(bot_settings["sub_unsupported_client_announce_text"]).strip():
        return get_user_note(user, bot_settings["sub_unsupported_client_announce_text"])
    if blocked_bs_addresses and str(bot_settings["sub_bs_limit_announce_text"]).strip():
        return get_user_note(user, bot_settings["sub_bs_limit_announce_text"])
    return announce_text


def build_subscription_response_headers(
    *,
    request: Request,
    user: UserResponse,
    bot_settings: dict,
    announce_text: str,
    subscription_userinfo: str,
    user_agent: str,
    build_content_disposition: Callable[[str], str],
    get_routing_header: Callable[[str, dict], dict],
) -> dict[str, str]:
    # Единая сборка subscription-заголовков для обоих /sub эндпоинтов.
    headers = {
        "content-disposition": build_content_disposition(user.username),
        "profile-web-page-url": bot_settings["sub_profile_url"] or str(request.url),
        "support-url": bot_settings["sub_support_url"],
        "profile-title": encode_title(bot_settings["sub_profile_title"]),
        "announce": encode_title(announce_text),
        "announce-url": bot_settings["bot_url"],
        "profile-update-interval": str(bot_settings["sub_update_interval"]),
        "subscription-userinfo": subscription_userinfo,
    }
    headers.update(get_routing_header(user_agent, bot_settings))
    headers.update(parse_custom_headers(bot_settings.get("sub_custom_headers") or ""))
    return headers


def resolve_incy_media_type(use_custom_json_default: bool) -> str:
    return "application/json" if use_custom_json_default else "text/plain"


def resolve_subscription_plan_by_user_agent(
    user_agent: str,
    *,
    use_custom_json_default: bool,
    use_custom_json_for_v2rayn: bool,
    use_custom_json_for_v2rayng: bool,
    use_custom_json_for_streisand: bool,
    use_custom_json_for_happ: bool,
) -> SubscriptionRenderPlan:
    # Весь UA-routing сконцентрирован здесь, чтобы не раздувать роутер.
    if re.match(r"^([Cc]lash-verge|[Cc]lash[-\.]?[Mm]eta|[Ff][Ll][Cc]lash|[Mm]ihomo)", user_agent):
        return SubscriptionRenderPlan("clash-meta", False, False, "text/yaml")
    if re.match(r"^([Cc]lash|[Ss]tash)", user_agent):
        return SubscriptionRenderPlan("clash", False, False, "text/yaml")
    if re.match(r"^(SFA|SFI|SFM|SFT|[Kk]aring|[Hh]iddify[Nn]ext)", user_agent):
        return SubscriptionRenderPlan("sing-box", False, False, "application/json")
    if re.match(r"^(SS|SSR|SSD|SSS|Outline|Shadowsocks|SSconf)", user_agent):
        return SubscriptionRenderPlan("outline", False, False, "application/json")

    v2rayn_match = re.match(r"^v2rayN/(\d+\.\d+)", user_agent)
    if (use_custom_json_default or use_custom_json_for_v2rayn) and v2rayn_match:
        version_str = v2rayn_match.group(1)
        if _version_gte(version_str, "6.40"):
            return SubscriptionRenderPlan("v2ray-json", False, False, "application/json")
        return SubscriptionRenderPlan("v2ray", True, False, "text/plain")

    v2rayng_match = re.match(r"^v2rayNG/(\d+\.\d+\.\d+)", user_agent)
    if (use_custom_json_default or use_custom_json_for_v2rayng) and v2rayng_match:
        version_str = v2rayng_match.group(1)
        if _version_gte(version_str, "1.8.29"):
            return SubscriptionRenderPlan("v2ray-json", False, False, "application/json")
        if _version_gte(version_str, "1.8.18"):
            return SubscriptionRenderPlan("v2ray-json", False, True, "application/json")
        return SubscriptionRenderPlan("v2ray", True, False, "text/plain")

    if re.match(r"^[Ss]treisand", user_agent):
        if use_custom_json_default or use_custom_json_for_streisand:
            return SubscriptionRenderPlan("v2ray-json", False, False, "application/json")
        return SubscriptionRenderPlan("v2ray", True, False, "text/plain")

    happ_match = re.match(r"^Happ/(\d+\.\d+\.\d+)", user_agent)
    if (use_custom_json_default or use_custom_json_for_happ) and happ_match:
        version_str = happ_match.group(1)
        if _version_gte(version_str, "1.63.1"):
            return SubscriptionRenderPlan("v2ray-json", False, False, "application/json")
        return SubscriptionRenderPlan("v2ray", True, False, "text/plain")

    if re.match(r"^[Ii][Nn][Cc][Yy]/", user_agent):
        return SubscriptionRenderPlan("incy", False, False, resolve_incy_media_type(use_custom_json_default))

    return SubscriptionRenderPlan("v2ray", True, False, "text/plain")


def resolve_subscription_plan_by_client_type(
    client_type: str,
    *,
    client_config: dict[str, SubscriptionClientConfigEntry],
    use_custom_json_default: bool,
) -> SubscriptionRenderPlan:
    # Явно заданный client_type (/{token}/{client_type}) → план рендера.
    config = client_config.get(client_type)
    if config is None:
        raise ValueError("Unknown client type")

    media_type = config["media_type"]
    if client_type == "incy":
        media_type = resolve_incy_media_type(use_custom_json_default)

    return SubscriptionRenderPlan(
        config_format=config["config_format"],
        as_base64=config["as_base64"],
        reverse=config["reverse"],
        media_type=media_type,
    )
