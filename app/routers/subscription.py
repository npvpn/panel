import re
from datetime import datetime, timezone
import math
from app.db.models import User
from distutils.version import LooseVersion
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Path, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import TimeoutError as SATimeoutError, OperationalError

from app import logger
from app.db import GetDB, Session, crud, get_db
from app.dependencies import get_validated_sub, validate_dates
from app.models.user import SubscriptionUserResponse, UserResponse
from app.subscription.share import encode_title, generate_subscription
from app.subscription.bot_settings import resolve_bot_settings
from app.templates import render_template
from app.utils.jwt import get_subscription_payload
from config import (
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


def get_user_note(user: UserResponse, note_template: str) -> str:
    """Return note from SUB_CLIENT_NOTE with <days_left> and <tg_id> placeholders."""
    if not note_template:
        return ""
    if "_" in user.username:
        note_template = note_template.replace("<tg_id>", user.username.split("_", 1)[0])
    expire_ts = int(user.expire or 0)
    if expire_ts <= 0:
        return note_template.replace("<days_left>", "0")
    now_ts = int(datetime.now(timezone.utc).timestamp())
    seconds_left = max(0, expire_ts - now_ts)
    days_left = math.ceil(seconds_left / 86400)
    return note_template.replace("<days_left>", str(days_left))


def resolve_subscription_context(token: str, db: Session):
    """
    Returns tuple: (dbuser or None, is_revoked: bool, created_at)
    - dbuser is None when token invalid/not found
    - is_revoked True when token is valid but revoked
    """
    sub = get_subscription_payload(token)
    if not sub:
        return None, False, None
    dbuser: User | None = crud.get_user(db, sub['username'])
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


def _update_user_sub_bg(user_id: int, user_agent: str) -> None:
    """
    Фоновый апдейт users.sub_updated_at / sub_last_user_agent.
    Запускается через FastAPI BackgroundTasks ПОСЛЕ ответа клиенту, чтобы
    одиночный UPDATE по строке users не блокировал горячий путь /sub/ и
    не приводил к 500 (1205 Lock wait timeout exceeded), когда параллельно
    с /sub/ идут массовые UPDATE'ы users из mailing_queue / record_usages /
    edit_user. Поля sub_updated_at и sub_last_user_agent читаются только
    админкой панели (telegram/utils/shared.py) для информации, никакая
    бизнес-логика на их актуальности не строится, поэтому потеря одного
    апдейта (или задержка ~ms) безопасна.
    """
    try:
        with GetDB() as db:
            dbuser = db.query(User).filter(User.id == user_id).first()
            if dbuser is None:
                return
            crud.update_user_sub(db, dbuser, user_agent)
    except (SATimeoutError, OperationalError) as exc:
        # Lock wait / pool timeout — поле обновит следующий /sub-запрос.
        logger.warning(
            "[sub.update_bg] skip user_id=%s due to %s: %s",
            user_id, type(exc).__name__, exc,
        )
    except Exception as exc:
        logger.warning(
            "[sub.update_bg] unexpected error user_id=%s: %s: %s",
            user_id, type(exc).__name__, exc,
        )


def get_routing_header(user_agent: str, dbuser: User) -> dict:
    """Build optional routing header for Happ/v2raytun clients."""
    routing_value = ""
    if re.search(r"v2raytun", user_agent or "", re.IGNORECASE):
        routing_value = str(settings.get("sub_routing_v2raytun") or "").strip()
    elif re.search(r"\bhapp(?:/|\b)", user_agent or "", re.IGNORECASE):
        routing_value = str(settings.get("sub_routing_happ") or "").strip()

    return {"routing": routing_value} if routing_value else {}


@router.get("/{token}/")
@router.get("/{token}", include_in_schema=False)
def user_subscription(
    request: Request,
    token: str,
    background_tasks: BackgroundTasks,
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
    is_expired = bool(dbuser.expire and dbuser.expire > 0 and dbuser.expire < int(datetime.now(timezone.utc).timestamp()))
    user: UserResponse = UserResponse.model_validate(dbuser)
    bot_settings = resolve_bot_settings(dbuser)
    bot_settings = resolve_bot_settings(dbuser)

    html_device_limited = False
    if not is_revoked and not is_expired and dbuser.device_limit:
        html_device_limited = crud.count_user_devices(db, dbuser) >= dbuser.device_limit

    accept_header = request.headers.get("Accept", "")
    if "text/html" in accept_header:
        if is_revoked:
            return HTMLResponse(
                render_template(
                    "sub/revoked.html",
                    {"bot_url": bot_settings["bot_url"]}
                )
            )
        if is_expired:
            return HTMLResponse(
                render_template(
                    "sub/expired.html",
                    {"bot_url": bot_settings["bot_url"]}
                )
            )
        if html_device_limited:
            return HTMLResponse(
                render_template(
                    "sub/device_limit.html",
                    {"bot_url": bot_settings["bot_url"]}
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
    if not is_revoked and not is_expired:
        registered, unsupported_client = crud.register_user_device(
            db, dbuser, x_hwid, x_device_os, x_ver_os, x_device_model, user_agent
        )
        device_limited = (not registered and not unsupported_client) or crud.is_device_limit_exceeded(db, dbuser)
    unsupported_blocks = unsupported_client and bool(dbuser.device_limit)
    if is_revoked or is_expired or device_limited or unsupported_blocks:
        user = get_empty_subscription_user(user)

    if not is_revoked and not is_expired:
        background_tasks.add_task(_update_user_sub_bg, dbuser.id, user_agent)
    announce_text = get_user_note(user, str(bot_settings["sub_client_note"])) or ""
    if is_revoked and str(bot_settings["sub_revoked_announce_text"]).strip():
        announce_text = bot_settings["sub_revoked_announce_text"]
    elif is_expired and str(bot_settings["sub_expired_announce_text"]).strip():
        announce_text = bot_settings["sub_expired_announce_text"]
    elif device_limited and str(bot_settings["sub_device_limit_announce_text"]).strip():
        announce_text = bot_settings["sub_device_limit_announce_text"]
    elif unsupported_blocks and str(bot_settings["sub_unsupported_client_announce_text"]).strip():
        announce_text = bot_settings["sub_unsupported_client_announce_text"]
    support_url = bot_settings["sub_support_url"]
    profile_title = bot_settings["sub_profile_title"]
   
    response_headers = {
        "content-disposition": build_content_disposition(user.username),
        "profile-web-page-url": bot_settings["sub_profile_url"] or str(request.url),
        "support-url": support_url,
        "profile-title": encode_title(profile_title),
        "announce": encode_title(announce_text),
        "announce-url": bot_settings["bot_url"],
        "profile-update-interval": str(bot_settings["sub_update_interval"]),
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(user).items()
        )
    }
    response_headers.update(get_routing_header(user_agent, bot_settings))

    def build_subscription(config_format: str, as_base64: bool, reverse: bool) -> str:
        return generate_subscription(
            user=user,
            config_format=config_format,
            as_base64=as_base64,
            reverse=reverse,
            revoked=is_revoked,
            expired=is_expired,
            device_limited=device_limited,
            unsupported_client=unsupported_blocks,
            settings=bot_settings,
        )

    if re.match(r'^([Cc]lash-verge|[Cc]lash[-\.]?[Mm]eta|[Ff][Ll][Cc]lash|[Mm]ihomo)', user_agent):
        conf = build_subscription("clash-meta", False, False)
        return Response(content=conf, media_type="text/yaml", headers=response_headers)

    elif re.match(r'^([Cc]lash|[Ss]tash)', user_agent):
        conf = build_subscription("clash", False, False)
        return Response(content=conf, media_type="text/yaml", headers=response_headers)

    elif re.match(r'^(SFA|SFI|SFM|SFT|[Kk]aring|[Hh]iddify[Nn]ext)', user_agent):
        conf = build_subscription("sing-box", False, False)
        return Response(content=conf, media_type="application/json", headers=response_headers)

    elif re.match(r'^(SS|SSR|SSD|SSS|Outline|Shadowsocks|SSconf)', user_agent):
        conf = build_subscription("outline", False, False)
        return Response(content=conf, media_type="application/json", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_V2RAYN) and re.match(r'^v2rayN/(\d+\.\d+)', user_agent):
        version_str = re.match(r'^v2rayN/(\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("6.40"):
            conf = build_subscription("v2ray-json", False, False)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = build_subscription("v2ray", True, False)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_V2RAYNG) and re.match(r'^v2rayNG/(\d+\.\d+\.\d+)', user_agent):
        version_str = re.match(r'^v2rayNG/(\d+\.\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("1.8.29"):
            conf = build_subscription("v2ray-json", False, False)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        elif LooseVersion(version_str) >= LooseVersion("1.8.18"):
            conf = build_subscription("v2ray-json", False, True)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = build_subscription("v2ray", True, False)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif re.match(r'^[Ss]treisand', user_agent):
        if USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_STREISAND:
            conf = build_subscription("v2ray-json", False, False)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = build_subscription("v2ray", True, False)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_HAPP) and re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent):
        version_str = re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("1.63.1"):
            conf = build_subscription("v2ray-json", False, False)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = build_subscription("v2ray", True, False)
            return Response(content=conf, media_type="text/plain", headers=response_headers)



    else:
        conf = build_subscription("v2ray", True, False)
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
    is_expired = bool(dbuser.expire and dbuser.expire > 0 and dbuser.expire < int(datetime.now(timezone.utc).timestamp()))
    user: UserResponse = UserResponse.model_validate(dbuser)

    device_limited = False
    unsupported_client = False
    registered = False
    if not is_revoked and not is_expired:
        registered, unsupported_client = crud.register_user_device(
            db, dbuser, x_hwid, x_device_os, x_ver_os, x_device_model, user_agent
        )
        device_limited = (not registered and not unsupported_client) or crud.is_device_limit_exceeded(db, dbuser)
    unsupported_blocks = unsupported_client and bool(dbuser.device_limit)
    if is_revoked or is_expired or device_limited or unsupported_blocks:
        user = get_empty_subscription_user(user)

    announce_text = get_user_note(user, str(bot_settings["sub_client_note"])) or ""
    if is_revoked and str(bot_settings["sub_revoked_announce_text"]).strip():
        announce_text = bot_settings["sub_revoked_announce_text"]
    elif is_expired and str(bot_settings["sub_expired_announce_text"]).strip():
        announce_text = bot_settings["sub_expired_announce_text"]
    elif device_limited and str(bot_settings["sub_device_limit_announce_text"]).strip():
        announce_text = bot_settings["sub_device_limit_announce_text"]
    elif unsupported_blocks and str(bot_settings["sub_unsupported_client_announce_text"]).strip():
        announce_text = bot_settings["sub_unsupported_client_announce_text"]
    support_url = bot_settings["sub_support_url"]
    profile_title = bot_settings["sub_profile_title"]
    response_headers = {
        "content-disposition": build_content_disposition(user.username),
        "profile-web-page-url": bot_settings["sub_profile_url"] or str(request.url),
        "support-url": support_url,
        "profile-title": encode_title(profile_title),
        "announce": encode_title(announce_text),
        "announce-url": bot_settings["bot_url"],
        "profile-update-interval": str(bot_settings["sub_update_interval"]),
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(user).items()
        )
    }
    response_headers.update(get_routing_header(user_agent, bot_settings))

    config = client_config.get(client_type)
    conf = generate_subscription(user=user,
                                 config_format=config["config_format"],
                                 as_base64=config["as_base64"],
                                 reverse=config["reverse"],
                                 revoked=is_revoked,
                                 expired=is_expired,
                                 device_limited=device_limited,
                                 unsupported_client=unsupported_blocks,
                                 settings=bot_settings)

    return Response(content=conf, media_type=config["media_type"], headers=response_headers)