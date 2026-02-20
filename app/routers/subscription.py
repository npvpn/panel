import base64
import json
import re
from datetime import datetime, timezone
import math
from distutils.version import LooseVersion
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, Response
from fastapi.responses import HTMLResponse

from app.db import Session, crud, get_db
from app.dependencies import get_validated_sub, validate_dates
from app.models.user import SubscriptionUserResponse, UserResponse
from app.subscription.share import encode_title, generate_subscription
from app.templates import render_template
from app.utils.jwt import get_subscription_payload
from config import (
    BOT_URL,
    SUB_CLIENT_NOTE,
    SUB_PROFILE_TITLE,
    SUB_SUPPORT_URL,
    SUB_UPDATE_INTERVAL,
    SUBSCRIPTION_PAGE_TEMPLATE,
    USE_CUSTOM_JSON_DEFAULT,
    USE_CUSTOM_JSON_FOR_HAPP,
    USE_CUSTOM_JSON_FOR_STREISAND,
    USE_CUSTOM_JSON_FOR_V2RAYN,
    USE_CUSTOM_JSON_FOR_V2RAYNG,
    XRAY_SUBSCRIPTION_PATH,
)

client_config = {
    "clash-meta": {"config_format": "clash-meta", "media_type": "text/yaml", "as_base64": False, "reverse": False},
    "sing-box": {"config_format": "sing-box", "media_type": "application/json", "as_base64": False, "reverse": False},
    "clash": {"config_format": "clash", "media_type": "text/yaml", "as_base64": False, "reverse": False},
    "v2ray": {"config_format": "v2ray", "media_type": "text/plain", "as_base64": True, "reverse": False},
    "outline": {"config_format": "outline", "media_type": "application/json", "as_base64": False, "reverse": False},
    "v2ray-json": {"config_format": "v2ray-json", "media_type": "application/json", "as_base64": False,
                   "reverse": False}
}

router = APIRouter(tags=['Subscription'], prefix=f'/{XRAY_SUBSCRIPTION_PATH}')


def get_user_note(user: UserResponse) -> str:
    """Return note from marzban env CLIENT_NOTE with <days_left> placeholder support."""
    note_template = SUB_CLIENT_NOTE
    if not note_template:
        return ""
    expire_ts = int(user.expire or 0)
    if expire_ts <= 0:
        return note_template.replace("<days_left>", "0")
    now_ts = int(datetime.now(timezone.utc).timestamp())
    seconds_left = max(0, expire_ts - now_ts)
    days_left = math.ceil(seconds_left / 86400)
    note_template = note_template.replace("<days_left>", str(days_left))
    return note_template
def resolve_subscription_context(token: str, db: Session):
    """
    Returns tuple: (dbuser or None, is_revoked: bool, created_at)
    - dbuser is None when token invalid/not found
    - is_revoked True when token is valid but revoked
    """
    sub = get_subscription_payload(token)
    if not sub:
        return None, False, None
    dbuser = crud.get_user(db, sub['username'])
    if not dbuser:
        return None, False, None
    # If token created before user record (e.g., renamed/recreated), treat as invalid
    if dbuser.created_at and sub.get('created_at') and dbuser.created_at > sub['created_at']:
        return None, False, None
    revoked = bool(dbuser.sub_revoked_at and sub.get('created_at') and dbuser.sub_revoked_at > sub['created_at'])
    return dbuser, revoked, sub.get('created_at')


def build_content_disposition(username: str) -> str:
    """Build RFC 5987 compatible Content-Disposition with ASCII fallback and UTF-8 filename*."""
    fallback = re.sub(r'[^A-Za-z0-9._-]+', '_', username or 'profile')
    utf8_quoted = quote(username or 'profile', safe='')
    return f'attachment; filename="{fallback}"; filename*=UTF-8''{utf8_quoted}'


def build_happ_routing_link(domains: list[str]) -> str:
    routing_profile = {
        "Name": "Split Tunneling",
        "GlobalProxy": "false",
        "ProxySites": [f"domain:{domain}" for domain in domains],
        "DomainStrategy": "IPIfNonMatch",
        "FakeDNS": "false",
    }
    payload = json.dumps(routing_profile, separators=(",", ":"), ensure_ascii=True).encode()
    encoded = base64.b64encode(payload).decode()
    return f"happ://routing/onadd/{encoded}"


def get_subscription_user_info(user: UserResponse) -> dict:
    """Retrieve user subscription information including upload, download, total data, and expiry."""
    return {
        "upload": 0,
        "download": user.used_traffic,
        "total": user.data_limit if user.data_limit is not None else 0,
        "expire": user.expire if user.expire is not None else 0,
    }


def get_empty_subscription_user(user: UserResponse) -> UserResponse:
    return user.model_copy(update={"proxies": {}, "inbounds": {}})


@router.get("/{token}/")
@router.get("/{token}", include_in_schema=False)
def user_subscription(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
    user_agent: str = Header(default=""),
    x_hwid: str | None = Header(default=None),
    x_device_os: str | None = Header(default=None),
    x_ver_os: str | None = Header(default=None),
    x_device_model: str | None = Header(default=None),
):
    """Provides a subscription link based on the user agent (Clash, V2Ray, etc.)."""
    dbuser, is_revoked, _ = resolve_subscription_context(token, db)
    if not dbuser:
        return Response(status_code=404)
    crud.ensure_subscription_token(db, dbuser)
    user: UserResponse = UserResponse.model_validate(dbuser)

    html_device_limited = False
    if not is_revoked and dbuser.device_limit:
        html_device_limited = crud.count_user_devices(db, dbuser) >= dbuser.device_limit

    accept_header = request.headers.get("Accept", "")
    if "text/html" in accept_header:
        if is_revoked:
            return HTMLResponse(
                render_template(
                    "sub/revoked.html",
                    {"bot_url": BOT_URL}
                )
            )
        if html_device_limited:
            return HTMLResponse(
                render_template(
                    "sub/device_limit.html",
                    {"bot_url": BOT_URL}
                )
            )
        return HTMLResponse(
            render_template(
                SUBSCRIPTION_PAGE_TEMPLATE,
                {"user": user}
            )
        )

    device_limited = False
    unsupported_client = False
    registered = False
    if not is_revoked:
        registered, unsupported_client = crud.register_user_device(
            db, dbuser, x_hwid, x_device_os, x_ver_os, x_device_model, user_agent
        )
        device_limited = (not registered and not unsupported_client) or crud.is_device_limit_exceeded(db, dbuser)
    if is_revoked or device_limited or unsupported_client:
        user = get_empty_subscription_user(user)

    if not is_revoked:
        crud.update_user_sub(db, dbuser, user_agent)
    announce_text = get_user_note(user) or ""
    if is_revoked:
        announce_text = f"Подписка отозвана. Запросите новую ссылку в боте. {BOT_URL}"
    elif device_limited:
        announce_text = f"Достигнут лимит устройств. Удалите старое устройство или увеличьте лимит в боте. {BOT_URL}"
    elif unsupported_client:
        announce_text = f"Это приложение не поддерживается. Установите другое."
    response_headers = {
        "content-disposition": build_content_disposition(user.username),
        "profile-web-page-url": str(request.url),
        "support-url": SUB_SUPPORT_URL,
        "profile-title": encode_title(SUB_PROFILE_TITLE),
        "announce": encode_title(announce_text),
        "announce-url": BOT_URL,
        "profile-update-interval": SUB_UPDATE_INTERVAL,
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(user).items()
        )
    }
    if re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent):
        response_headers["routing"] = build_happ_routing_link(["youtube.com", "openai.com"])
    if re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent):
        response_headers["routing"] = build_happ_routing_link(["youtube.com", "openai.com"])

    if re.match(r'^([Cc]lash-verge|[Cc]lash[-\.]?[Mm]eta|[Ff][Ll][Cc]lash|[Mm]ihomo)', user_agent):
        conf = generate_subscription(
            user=user,
            config_format="clash-meta",
            as_base64=False,
            reverse=False,
            revoked=is_revoked,
            device_limited=device_limited,
            unsupported_client=unsupported_client
        )
        return Response(content=conf, media_type="text/yaml", headers=response_headers)

    elif re.match(r'^([Cc]lash|[Ss]tash)', user_agent):
        conf = generate_subscription(
            user=user,
            config_format="clash",
            as_base64=False,
            reverse=False,
            revoked=is_revoked,
            device_limited=device_limited,
            unsupported_client=unsupported_client
        )
        return Response(content=conf, media_type="text/yaml", headers=response_headers)

    elif re.match(r'^(SFA|SFI|SFM|SFT|[Kk]aring|[Hh]iddify[Nn]ext)', user_agent):
        conf = generate_subscription(
            user=user,
            config_format="sing-box",
            as_base64=False,
            reverse=False,
            revoked=is_revoked,
            device_limited=device_limited,
            unsupported_client=unsupported_client
        )
        return Response(content=conf, media_type="application/json", headers=response_headers)

    elif re.match(r'^(SS|SSR|SSD|SSS|Outline|Shadowsocks|SSconf)', user_agent):
        conf = generate_subscription(
            user=user,
            config_format="outline",
            as_base64=False,
            reverse=False,
            revoked=is_revoked,
            device_limited=device_limited,
            unsupported_client=unsupported_client
        )
        return Response(content=conf, media_type="application/json", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_V2RAYN) and re.match(r'^v2rayN/(\d+\.\d+)', user_agent):
        version_str = re.match(r'^v2rayN/(\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("6.40"):
            conf = generate_subscription(
                user=user,
                config_format="v2ray-json",
                as_base64=False,
                reverse=False,
                revoked=is_revoked,
                device_limited=device_limited,
                unsupported_client=unsupported_client
            )
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(
                user=user,
                config_format="v2ray",
                as_base64=True,
                reverse=False,
                revoked=is_revoked,
                device_limited=device_limited,
                unsupported_client=unsupported_client
            )
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_V2RAYNG) and re.match(r'^v2rayNG/(\d+\.\d+\.\d+)', user_agent):
        version_str = re.match(r'^v2rayNG/(\d+\.\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("1.8.29"):
            conf = generate_subscription(
                user=user,
                config_format="v2ray-json",
                as_base64=False,
                reverse=False,
                revoked=is_revoked,
                device_limited=device_limited,
                unsupported_client=unsupported_client
            )
            return Response(content=conf, media_type="application/json", headers=response_headers)
        elif LooseVersion(version_str) >= LooseVersion("1.8.18"):
            conf = generate_subscription(
                user=user,
                config_format="v2ray-json",
                as_base64=False,
                reverse=True,
                revoked=is_revoked,
                device_limited=device_limited,
                unsupported_client=unsupported_client
            )
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(
                user=user,
                config_format="v2ray",
                as_base64=True,
                reverse=False,
                revoked=is_revoked,
                device_limited=device_limited,
                unsupported_client=unsupported_client
            )
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif re.match(r'^[Ss]treisand', user_agent):
        if USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_STREISAND:
            conf = generate_subscription(
                user=user,
                config_format="v2ray-json",
                as_base64=False,
                reverse=False,
                revoked=is_revoked,
                device_limited=device_limited,
                unsupported_client=unsupported_client
            )
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(
                user=user,
                config_format="v2ray",
                as_base64=True,
                reverse=False,
                revoked=is_revoked,
                device_limited=device_limited,
                unsupported_client=unsupported_client
            )
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_HAPP) and re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent):
        version_str = re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("1.63.1"):
            conf = generate_subscription(
                user=user,
                config_format="v2ray-json",
                as_base64=False,
                reverse=False,
                revoked=is_revoked,
                device_limited=device_limited,
                unsupported_client=unsupported_client
            )
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(
                user=user,
                config_format="v2ray",
                as_base64=True,
                reverse=False,
                revoked=is_revoked,
                device_limited=device_limited
            )
            return Response(content=conf, media_type="text/plain", headers=response_headers)



    else:
        conf = generate_subscription(
            user=user,
            config_format="v2ray",
            as_base64=True,
            reverse=False,
            revoked=is_revoked,
            device_limited=device_limited,
            unsupported_client=unsupported_client
        )
        return Response(content=conf, media_type="text/plain", headers=response_headers)


@router.get("/{token}/info", response_model=SubscriptionUserResponse)
def user_subscription_info(
    dbuser: UserResponse = Depends(get_validated_sub),
):
    """Retrieves detailed information about the user's subscription."""
    return dbuser


@router.get("/{token}/usage")
def user_get_usage(
    dbuser: UserResponse = Depends(get_validated_sub),
    start: str = "",
    end: str = "",
    db: Session = Depends(get_db)
):
    """Fetches the usage statistics for the user within a specified date range."""
    start, end = validate_dates(start, end)

    usages = crud.get_user_usages(db, dbuser, start, end)

    return {"usages": usages, "username": dbuser.username}


@router.get("/{token}/{client_type}")
def user_subscription_with_client_type(
    request: Request,
    token: str,
    client_type: str = Path(..., regex="sing-box|clash-meta|clash|outline|v2ray|v2ray-json"),
    db: Session = Depends(get_db),
    user_agent: str = Header(default=""),
    x_hwid: str | None = Header(default=None),
    x_device_os: str | None = Header(default=None),
    x_ver_os: str | None = Header(default=None),
    x_device_model: str | None = Header(default=None),
):
    """Provides a subscription link based on the specified client type (e.g., Clash, V2Ray)."""
    dbuser, is_revoked, _ = resolve_subscription_context(token, db)
    if not dbuser:
        return Response(status_code=404)
    crud.ensure_subscription_token(db, dbuser)
    user: UserResponse = UserResponse.model_validate(dbuser)

    device_limited = False
    unsupported_client = False
    registered = False
    if not is_revoked:
        registered, unsupported_client = crud.register_user_device(
            db, dbuser, x_hwid, x_device_os, x_ver_os, x_device_model, user_agent
        )
        device_limited = (not registered and not unsupported_client) or crud.is_device_limit_exceeded(db, dbuser)
    if is_revoked or device_limited or unsupported_client:
        user = get_empty_subscription_user(user)

    announce_text = get_user_note(user) or ""
    if is_revoked:
        announce_text = f"Подписка отозвана. Запросите новую ссылку в боте. {BOT_URL}"
    elif device_limited:
        announce_text = f"Достигнут лимит устройств. Удалите старое устройство или увеличьте лимит в боте. {BOT_URL}"
    elif unsupported_client:
        announce_text = f"Это приложение не поддерживается. Установите другое."
    response_headers = {
        "content-disposition": build_content_disposition(user.username),
        "profile-web-page-url": str(request.url),
        "support-url": SUB_SUPPORT_URL,
        "profile-title": encode_title(SUB_PROFILE_TITLE),
        "announce": encode_title(announce_text),
        "announce-url": BOT_URL,
        "profile-update-interval": SUB_UPDATE_INTERVAL,
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(user).items()
        )
    }

    config = client_config.get(client_type)
    conf = generate_subscription(user=user,
                                 config_format=config["config_format"],
                                 as_base64=config["as_base64"],
                                 reverse=config["reverse"],
                                 revoked=is_revoked,
                                 device_limited=device_limited,
                                 unsupported_client=unsupported_client)

    return Response(content=conf, media_type=config["media_type"], headers=response_headers)