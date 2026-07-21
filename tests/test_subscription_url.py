from __future__ import annotations

import app.subscription.subscription_url as subscription_url
from app.subscription.subscription_url import (
    build_subscription_url,
    normalize_subscription_domain,
    resolve_subscription_url_prefix,
)


def test_normalize_subscription_domain_strips_scheme_and_slashes():
    assert normalize_subscription_domain("https://example.net/") == "example.net"
    assert normalize_subscription_domain("http://example.net") == "example.net"
    assert normalize_subscription_domain("example.net") == "example.net"
    assert normalize_subscription_domain("  ") == ""
    assert normalize_subscription_domain(None) == ""


def test_resolve_prefix_prefers_bot_domain(monkeypatch):
    monkeypatch.setattr(subscription_url, "XRAY_SUBSCRIPTION_URL_PREFIX", "https://env.example.com")
    assert resolve_subscription_url_prefix({"sub_subscription_domain": "example.net"}) == "https://example.net"
    assert resolve_subscription_url_prefix({"sub_subscription_domain": "https://other.net/"}) == "https://other.net"


def test_resolve_prefix_falls_back_to_env(monkeypatch):
    monkeypatch.setattr(subscription_url, "XRAY_SUBSCRIPTION_URL_PREFIX", "https://env.example.com")
    assert resolve_subscription_url_prefix({"sub_subscription_domain": ""}) == "https://env.example.com"
    assert resolve_subscription_url_prefix({}) == "https://env.example.com"
    assert resolve_subscription_url_prefix(None) == "https://env.example.com"


def test_resolve_prefix_empty_when_no_domain_and_no_env(monkeypatch):
    monkeypatch.setattr(subscription_url, "XRAY_SUBSCRIPTION_URL_PREFIX", "")
    assert resolve_subscription_url_prefix({"sub_subscription_domain": ""}) == ""
    assert resolve_subscription_url_prefix(None) == ""


def test_build_subscription_url_with_bot_domain(monkeypatch):
    monkeypatch.setattr(subscription_url, "XRAY_SUBSCRIPTION_PATH", "sub")
    monkeypatch.setattr(subscription_url, "XRAY_SUBSCRIPTION_URL_PREFIX", "")
    assert (
        build_subscription_url("tok123", bot_settings={"sub_subscription_domain": "example.net"})
        == "https://example.net/sub/tok123"
    )


def test_build_subscription_url_path_only_without_prefix(monkeypatch):
    monkeypatch.setattr(subscription_url, "XRAY_SUBSCRIPTION_PATH", "sub")
    monkeypatch.setattr(subscription_url, "XRAY_SUBSCRIPTION_URL_PREFIX", "")
    assert build_subscription_url("tok123") == "/sub/tok123"
    assert build_subscription_url(None) == ""
    assert build_subscription_url("") == ""


def test_build_subscription_url_explicit_prefix_overrides_settings(monkeypatch):
    monkeypatch.setattr(subscription_url, "XRAY_SUBSCRIPTION_PATH", "sub")
    assert (
        build_subscription_url(
            "tok123",
            "https://forced.example",
            bot_settings={"sub_subscription_domain": "ignored.net"},
        )
        == "https://forced.example/sub/tok123"
    )
