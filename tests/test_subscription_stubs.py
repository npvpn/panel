"""Заглушки подписки: выбор текста и содержимое v2ray/v2ray-json stub."""

from __future__ import annotations

import base64
import json

import pytest

from app.subscription.sub_stub import build_v2ray_status_stub, pick_status_stub_text_list

STUB_SETTINGS = {
    "sub_revoked_server_text": ["Эта ссылка не активна"],
    "sub_expired_server_text": ["Подписка истекла"],
    "sub_device_limit_server_text": ["Достигнут лимит устройств"],
    "sub_unsupported_client_server_text": ["Это приложение не поддерживается, Установите другое"],
}


def test_pick_status_stub_revoked_has_top_priority():
    """Revoked важнее expired/unsupported/device_limit."""
    text = pick_status_stub_text_list(
        revoked=True,
        expired=True,
        device_limited_hard=True,
        unsupported_client=True,
        settings=STUB_SETTINGS,
    )
    assert text == STUB_SETTINGS["sub_revoked_server_text"]


def test_pick_status_stub_expired_before_device_limit():
    text = pick_status_stub_text_list(
        revoked=False,
        expired=True,
        device_limited_hard=True,
        unsupported_client=True,
        settings=STUB_SETTINGS,
    )
    assert text == STUB_SETTINGS["sub_expired_server_text"]


def test_pick_status_stub_device_limit_before_unsupported():
    text = pick_status_stub_text_list(
        revoked=False,
        expired=False,
        device_limited_hard=True,
        unsupported_client=True,
        settings=STUB_SETTINGS,
    )
    assert text == STUB_SETTINGS["sub_device_limit_server_text"]


def test_pick_status_stub_unsupported_when_only_flag_set():
    text = pick_status_stub_text_list(
        revoked=False,
        expired=False,
        device_limited_hard=False,
        unsupported_client=True,
        settings=STUB_SETTINGS,
    )
    assert text == STUB_SETTINGS["sub_unsupported_client_server_text"]


def test_pick_status_stub_empty_when_no_flags():
    text = pick_status_stub_text_list(
        revoked=False,
        expired=False,
        device_limited_hard=False,
        unsupported_client=False,
        settings=STUB_SETTINGS,
    )
    assert text == []


def test_build_v2ray_status_stub_v2ray_contains_remark():
    """v2ray base64 stub содержит текст заглушки в remark ссылки."""
    from urllib.parse import unquote

    remark = STUB_SETTINGS["sub_unsupported_client_server_text"][0]
    payload = build_v2ray_status_stub([remark], "v2ray", as_base64=True)
    decoded = base64.b64decode(payload).decode()
    fragment = decoded.rsplit("#", 1)[-1]
    assert unquote(fragment) == remark
    assert "0.0.0.0" in decoded
    assert "00000000-0000-0000-0000-000000000000" in decoded


def test_build_v2ray_status_stub_v2ray_json_contains_remark():
    """v2ray-json stub содержит remark в JSON (нужны шаблоны v2ray)."""
    try:
        remark = STUB_SETTINGS["sub_device_limit_server_text"][0]
        payload = build_v2ray_status_stub([remark], "v2ray-json", as_base64=False)
    except Exception as exc:
        pytest.skip(f"v2ray-json stub deps unavailable: {exc}")
    data = json.loads(payload)
    assert data[0]["remarks"] == remark


def test_build_v2ray_status_stub_empty_v2ray_returns_empty_base64():
    assert build_v2ray_status_stub([], "v2ray", as_base64=True) == base64.b64encode(b"").decode()


def test_build_v2ray_status_stub_empty_v2ray_json_returns_empty_array():
    assert build_v2ray_status_stub([], "v2ray-json", as_base64=False) == "[]"
